"""
PyreSwarm - Algılama Katmanı Soyutlaması (Perception Abstraction Layer)
BaseDetector soyut sınıfı, UltralyticsDetector ve MockDetector adaptörleri.
Gelecekte ONNX ve TensorRT adaptörleri kolayca eklenebilir.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import os
import math
import numpy as np
import cv2

try:
    import torch
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


@dataclass
class DetectionResult:
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]              # x1, y1, x2, y2 (piksel)
    box_area_ratio: float                        # Kutu alanının tüm görüntüye oranı [0.0, 1.0]
    estimated_gps: Optional[Tuple[float, float]] = None # (lat, lon)


class BaseDetector(ABC):
    """Tüm nesne algılayıcılar için ortak temel sınıf."""

    @abstractmethod
    def detect(
        self,
        frame: np.ndarray,
        drone_lat: float,
        drone_lon: float,
        drone_alt: float,
        drone_yaw_deg: float,
        gimbal_pitch_deg: float = -90.0,
        camera_hfov_deg: float = 84.0
    ) -> Tuple[List[DetectionResult], float, np.ndarray]:
        """
        Kamera karesini analiz eder.
        Döndürür: (detections, total_score, annotated_frame)
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Model metadata ve performans bilgilerini döndürür."""
        pass


class UltralyticsDetector(BaseDetector):
    """
    YOLOv8 best.pt modeli ile gerçek zamanlı PyTorch inferansı gerçekleştiren adaptör.
    [MEASURED]
    """

    METERS_PER_DEGREE = 111139.0

    def __init__(
        self,
        model_path: str = "best.pt",
        conf_threshold: float = 0.25,
        device: Optional[str] = None
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.model = None

        if not YOLO_AVAILABLE or not os.path.exists(model_path):
            print(f"[UltralyticsDetector] Model yüklenemedi: {model_path} (Fallback mod devrede)")
            return

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        try:
            self.model = YOLO(model_path)
            # Warmup
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            self.model(dummy, verbose=False, device=self.device)
        except Exception as e:
            print(f"[UltralyticsDetector] Model init hatası: {e}")
            self.model = None

    def detect(
        self,
        frame: np.ndarray,
        drone_lat: float,
        drone_lon: float,
        drone_alt: float,
        drone_yaw_deg: float,
        gimbal_pitch_deg: float = -90.0,
        camera_hfov_deg: float = 84.0
    ) -> Tuple[List[DetectionResult], float, np.ndarray]:
        h, w = frame.shape[:2]
        detections: List[DetectionResult] = []
        annotated_frame = frame.copy()
        total_score = 0.0

        if self.model is None or frame is None or frame.size == 0:
            return detections, total_score, annotated_frame

        try:
            results = self.model(
                frame,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False
            )

            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    cls_name = self.model.names.get(cls_id, f"class_{cls_id}")
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]

                    area_ratio = ((x2 - x1) * (y2 - y1)) / float(w * h)
                    center_x = (x1 + x2) / 2.0
                    center_y = (y1 + y2) / 2.0

                    est_gps = self._ray_cast_gps(
                        px=center_x, py=center_y, img_w=w, img_h=h,
                        lat=drone_lat, lon=drone_lon, alt=drone_alt,
                        yaw_deg=drone_yaw_deg, hfov_deg=camera_hfov_deg
                    )

                    det = DetectionResult(
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        box_area_ratio=area_ratio,
                        estimated_gps=est_gps
                    )
                    detections.append(det)

                    # Alev katsayısı 1.0, Duman 0.8
                    weight = 1.0 if "fire" in cls_name.lower() else 0.8
                    score = weight * conf * (0.5 + 0.5 * math.sqrt(area_ratio * 10.0))
                    total_score += score

            # Kutu çizimi
            for d in detections:
                x1, y1, x2, y2 = d.bbox
                color = (0, 69, 255) if "fire" in d.class_name.lower() else (200, 200, 200)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    annotated_frame, f"{d.class_name.upper()} %{int(d.confidence*100)}",
                    (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1
                )

        except Exception as e:
            print(f"[UltralyticsDetector] İnferans hatası: {e}")

        return detections, total_score, annotated_frame

    def _ray_cast_gps(
        self, px: float, py: float, img_w: int, img_h: int,
        lat: float, lon: float, alt: float, yaw_deg: float, hfov_deg: float
    ) -> Tuple[float, float]:
        """Pinhole ray-casting ile piksel zemin izdüşümü."""
        vfov_deg = hfov_deg * (float(img_h) / float(img_w))
        rad_hfov_2 = math.radians(hfov_deg / 2.0)
        rad_vfov_2 = math.radians(vfov_deg / 2.0)

        norm_x = (px - (img_w / 2.0)) / (img_w / 2.0)
        norm_y = ((img_h / 2.0) - py) / (img_h / 2.0)

        dx_cam = alt * math.tan(norm_x * rad_hfov_2)
        dy_cam = alt * math.tan(norm_y * rad_vfov_2)

        rad_yaw = math.radians(yaw_deg)
        dx_ground = dx_cam * math.cos(rad_yaw) + dy_cam * math.sin(rad_yaw)
        dy_ground = -dx_cam * math.sin(rad_yaw) + dy_cam * math.cos(rad_yaw)

        cos_lat = math.cos(math.radians(lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat
        est_lat = lat + (dy_ground / self.METERS_PER_DEGREE)
        est_lon = lon + (dx_ground / m_per_deg_lon)

        return round(est_lat, 6), round(est_lon, 6)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "type": "Ultralytics YOLOv8",
            "model_path": self.model_path,
            "device": self.device,
            "classes": self.model.names if self.model else ["smoke", "fire"],
            "parameters": 3011238,
            "gflops": 8.19
        }


class MockDetector(BaseDetector):
    """
    Birim testleri ve deterministik simülasyonlar için sentetik algılayıcı adaptörü.
    İstenilen konumlarda önceden belirlenmiş güven skorları üretir.
    [SIMULATED]
    """

    def __init__(self, targets: Optional[List[Tuple[float, float, float]]] = None):
        self.targets = targets or []  # [(lat, lon, conf), ...]

    def detect(
        self,
        frame: np.ndarray,
        drone_lat: float,
        drone_lon: float,
        drone_alt: float,
        drone_yaw_deg: float,
        gimbal_pitch_deg: float = -90.0,
        camera_hfov_deg: float = 84.0
    ) -> Tuple[List[DetectionResult], float, np.ndarray]:
        detections: List[DetectionResult] = []
        total_score = 0.0
        annotated_frame = frame.copy() if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)

        # En yakın hedefe olan mesafeyi kontrol et
        fov_radius_deg = (drone_alt * 0.9) / 111139.0

        for t_lat, t_lon, conf in self.targets:
            dist_deg = math.hypot(drone_lat - t_lat, drone_lon - t_lon)
            if dist_deg <= fov_radius_deg:
                det = DetectionResult(
                    class_id=1,
                    class_name="fire",
                    confidence=conf,
                    bbox=(200, 150, 440, 330),
                    box_area_ratio=0.15,
                    estimated_gps=(t_lat, t_lon)
                )
                detections.append(det)
                total_score += conf

        return detections, total_score, annotated_frame

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "type": "Mock Deterministic Detector",
            "targets_count": len(self.targets)
        }
