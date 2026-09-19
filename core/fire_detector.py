"""
PyreSwarm - YOLOv8 Yangın ve Duman Algılayıcı (Fire Detector)
best.pt modeli ile gerçek zamanlı görüntü işleme, confidence üretimi ve zemin GPS kestirimi.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
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
    bbox: Tuple[int, int, int, int]    # x1, y1, x2, y2 (pixel)
    box_area_ratio: float              # Nesnenin tüm görüntüye oranı (0.0 - 1.0)
    estimated_gps: Optional[Tuple[float, float]] = None  # (lat, lon)


class FireDetector:
    """
    YOLOv8 tabanlı yangın ve duman algılama motoru.
    Frame başına yangın skoru üretir ve zemin koordinatlarını kestirir.
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

        if not YOLO_AVAILABLE:
            print("[FireDetector] UYARI: ultralytics veya torch bulunamadı, fallback modu devrede.")
            return

        if not os.path.exists(model_path):
            print(f"[FireDetector] UYARI: Model dosyası bulunamadı: {model_path}")
            return

        # Donanım hızlandırma seçimi
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        try:
            print(f"[FireDetector] YOLO modeli yükleniyor: {model_path} (Cihaz: {self.device})...")
            self.model = YOLO(model_path)
            # Isınma (Warmup) inferansı
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            self.model(dummy, verbose=False, device=self.device)
            print(f"[FireDetector] Model hazır! Sınıflar: {self.model.names}")
        except Exception as e:
            print(f"[FireDetector] Model yüklenirken hata: {e}")
            self.model = None

    def detect(
        self,
        frame: np.ndarray,
        drone_lat: float = 0.0,
        drone_lon: float = 0.0,
        drone_alt: float = 50.0,
        drone_yaw_deg: float = 0.0,
        gimbal_pitch_deg: float = -90.0,  # -90 tam dikey alta bakar (nadir)
        camera_hfov_deg: float = 84.0     # Standart drone kamera yatay görüş açısı
    ) -> Tuple[List[DetectionResult], float, np.ndarray]:
        """
        Kamera karesini analiz eder.
        Döndürür:
          - detections: Algılanan nesnelerin listesi
          - total_fitness_score: PSO hedefi için birleşik yangın skoru (0.0 - 1.0+)
          - annotated_frame: HUD ve tespit kutucukları çizilmiş görüntü
        """
        if frame is None or frame.size == 0:
            return [], 0.0, frame
        h, w = frame.shape[:2]
        detections: List[DetectionResult] = []
        annotated_frame = frame.copy()
        total_fitness_score = 0.0

        if self.model is None or frame is None or frame.size == 0:
            return detections, min(1.0, total_fitness_score), annotated_frame

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
                    if not any(label in cls_name.lower() for label in ("fire", "smoke", "flame")):
                        continue
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]

                    box_w = max(0, x2 - x1)
                    box_h = max(0, y2 - y1)
                    box_area = box_w * box_h
                    area_ratio = box_area / float(w * h)

                    # Zemin koordinatı kestirimi
                    center_x = (x1 + x2) / 2.0
                    center_y = (y1 + y2) / 2.0
                    est_gps = self._estimate_ground_gps(
                        px=center_x,
                        py=center_y,
                        img_w=w,
                        img_h=h,
                        lat=drone_lat,
                        lon=drone_lon,
                        alt=drone_alt,
                        yaw_deg=drone_yaw_deg,
                        pitch_deg=gimbal_pitch_deg,
                        hfov_deg=camera_hfov_deg
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

                    # Sınıf ağırlığı: Yangın (fire) daha kritiktir, duman (smoke) öncül habercidir
                    weight = 1.0 if "fire" in cls_name.lower() else 0.8
                    # Güven skoru ve alan büyüklüğü ile orantılı skor
                    score = weight * conf * (0.5 + 0.5 * math.sqrt(area_ratio * 10.0))
                    total_fitness_score += score

            # Görselleştirme / HUD çizimi
            annotated_frame = self._draw_hud(
                annotated_frame, detections, drone_alt, drone_yaw_deg, total_fitness_score
            )

        except Exception as e:
            print(f"[FireDetector] Inferans hatası: {e}")

        return detections, min(1.0, total_fitness_score), annotated_frame

    def _estimate_ground_gps(
        self,
        px: float,
        py: float,
        img_w: int,
        img_h: int,
        lat: float,
        lon: float,
        alt: float,
        yaw_deg: float,
        pitch_deg: float,
        hfov_deg: float
    ) -> Tuple[float, float]:
        """
        Piksel koordinatından yeryüzündeki yaklaşık GPS koordinatını hesaplar (Pin-hole ray projection).
        """
        # Görüntü merkezine göre normalize ofset (-1.0 ile +1.0 arası)
        norm_x = (px - (img_w / 2.0)) / (img_w / 2.0)
        norm_y = ((img_h / 2.0) - py) / (img_h / 2.0)

        vfov_rad = math.radians(hfov_deg * (img_h / float(img_w)))
        hfov_rad = math.radians(hfov_deg)

        # Kamera koordinat sistemi açıları
        angle_x = norm_x * (hfov_rad / 2.0)
        angle_y = norm_y * (vfov_rad / 2.0)

        # Basitleştirilmiş dikey yere bakış (Nadir gimbal) kestirimi
        ground_dx = alt * math.tan(angle_x)
        ground_dy = alt * math.tan(angle_y)

        # Drone heading (yaw) açısına göre döndür
        yaw_rad = math.radians(yaw_deg)
        rot_dx = ground_dx * math.cos(yaw_rad) + ground_dy * math.sin(yaw_rad)
        rot_dy = -ground_dx * math.sin(yaw_rad) + ground_dy * math.cos(yaw_rad)

        # Metreyi GPS derecesine çevir
        cos_lat = math.cos(math.radians(lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        target_lat = lat + (rot_dy / self.METERS_PER_DEGREE)
        target_lon = lon + (rot_dx / m_per_deg_lon)

        return target_lat, target_lon

    def _draw_hud(
        self,
        img: np.ndarray,
        detections: List[DetectionResult],
        alt: float,
        yaw: float,
        fitness: float
    ) -> np.ndarray:
        """Görüntü üzerine askeri/havacılık tarzı HUD ve bounding box çizer."""
        out = img.copy()
        h, w = out.shape[:2]

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            is_fire = "fire" in det.class_name.lower()
            color = (0, 0, 255) if is_fire else (255, 140, 0)  # BGR formatı

            # Köşeli modern kutu
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

            label = f"{det.class_name.upper()} {det.confidence:.2f}"
            if det.estimated_gps:
                label += f" ({det.estimated_gps[0]:.4f},{det.estimated_gps[1]:.4f})"

            t_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x1, y1 - 20), (x1 + t_size[0] + 6, y1), color, -1)
            cv2.putText(out, label, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # Üst Bilgi Barı (HUD)
        overlay = out.copy()
        cv2.rectangle(overlay, (0, 0), (w, 32), (15, 20, 25), -1)
        cv2.addWeighted(overlay, 0.75, out, 0.25, 0, out)

        hud_text = f"ALT: {alt:.1f}m | YAW: {yaw:.0f}deg | SCORE: {fitness:.2f} | DETECTIONS: {len(detections)}"
        cv2.putText(out, hud_text, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 1, cv2.LINE_AA)

        # Merkez Nişangahı (Reticle)
        cx, cy = w // 2, h // 2
        cv2.line(out, (cx - 15, cy), (cx + 15, cy), (0, 255, 180), 1)
        cv2.line(out, (cx, cy - 15), (cx, cy + 15), (0, 255, 180), 1)
        cv2.circle(out, (cx, cy), 8, (0, 255, 180), 1)

        return out
