"""
PyreSwarm - Vatandaş & Gönüllü Drone Entegrasyon Köprüsü (Volunteer Drone Bridge)
Operasyon bölgesine sonradan gelen üçüncü parti/vatandaş drone'ların sürüye anında tak-çalıştır katılmasını sağlar.
"""

import time
import math
from typing import Optional, Dict, Any
import numpy as np
import cv2

from hardware.drone_base import BaseDrone, DroneMode, DroneType, DroneTelemetry


class VolunteerDrone(BaseDrone):
    """
    Sürüye dışarıdan katılan gönüllü drone.
    Mobil tarayıcı, akıllı telefon veya üçüncü parti kumanda üzerinden
    REST/WebSocket ile telemetri besler ve PSO yönlendirme komutlarını alır.
    """

    METERS_PER_DEGREE = 111139.0

    def __init__(
        self,
        drone_id: str,
        pilot_name: str,
        initial_lat: float,
        initial_lon: float,
        initial_alt: float = 30.0,
        camera_stream_url: Optional[str] = None
    ):
        super().__init__(drone_id=drone_id, drone_type=DroneType.VOLUNTEER)
        self.pilot_name = pilot_name
        self.camera_stream_url = camera_stream_url

        self.telemetry.lat = initial_lat
        self.telemetry.lon = initial_lon
        self.telemetry.alt = initial_alt
        self.telemetry.battery_percentage = 100.0
        self.telemetry.is_armed = True
        self.telemetry.is_in_air = True
        self.mode = DroneMode.MISSION_PSO
        self.telemetry.mode = self.mode

        # Pilot için yönlendirme komutu (Hedef Hız ve Yön)
        self.assigned_target_vx = 0.0
        self.assigned_target_vy = 0.0
        self.assigned_target_vz = 0.0
        self.assigned_target_alt = initial_alt
        self.assigned_heading = 0.0

        self._cap = None
        if self.camera_stream_url:
            try:
                self._cap = cv2.VideoCapture(self.camera_stream_url)
            except Exception:
                self._cap = None

        # Fallback sentetik orman görüntüsü
        self._default_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self._default_frame[:, :] = (30, 80, 40)

    def connect(self) -> bool:
        self.mode = DroneMode.MISSION_PSO
        self.telemetry.mode = self.mode
        return True

    def disconnect(self):
        if self._cap:
            self._cap.release()
        self.mode = DroneMode.DISCONNECTED
        self.telemetry.mode = self.mode

    def arm(self) -> bool:
        self.telemetry.is_armed = True
        return True

    def disarm(self) -> bool:
        self.telemetry.is_armed = False
        return True

    def takeoff(self, target_alt: float = 30.0) -> bool:
        self.telemetry.alt = target_alt
        self.telemetry.is_in_air = True
        return True

    def land(self) -> bool:
        self.mode = DroneMode.LANDING
        self.telemetry.mode = self.mode
        return True

    def return_to_launch(self) -> bool:
        self.mode = DroneMode.RTL
        self.telemetry.mode = self.mode
        return True

    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        """PSO motorundan gelen komutu pilota/otopilota iletilmek üzere saklar."""
        self.assigned_target_vx = vx
        self.assigned_target_vy = vy
        self.assigned_target_vz = vz
        if math.hypot(vx, vy) > 0.2:
            self.assigned_heading = (math.degrees(math.atan2(vx, vy)) + 360.0) % 360.0

        # Eğer canlı pilot henüz GPS beslemiyorsa yumuşak simülasyon hareketi uygula
        dt = 0.5
        cos_lat = math.cos(math.radians(self.telemetry.lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        self.telemetry.vx = vx
        self.telemetry.vy = vy
        self.telemetry.vz = vz
        self.telemetry.lon += (vx * dt) / m_per_deg_lon
        self.telemetry.lat += (vy * dt) / self.METERS_PER_DEGREE
        self.telemetry.alt = max(5.0, self.telemetry.alt + vz * dt)
        self.telemetry.speed = math.hypot(vx, vy)
        self.telemetry.heading = self.assigned_heading

        return True

    def goto_coordinate(self, lat: float, lon: float, alt: float, speed: float = 8.0) -> bool:
        self.assigned_target_alt = alt
        return True

    def update_from_external(self, lat: float, lon: float, alt: float, battery: float = 100.0):
        """Vatandaşın telefonundan veya otopilotundan gelen gerçek GPS telemetrisi."""
        self.telemetry.lat = lat
        self.telemetry.lon = lon
        self.telemetry.alt = alt
        self.telemetry.battery_percentage = battery
        self.telemetry.last_heartbeat = time.time()

    def update_camera_frame(self, frame: np.ndarray):
        """Web veya telefon kamerasından gelen görüntüyü günceller."""
        if frame is not None and frame.size > 0:
            self._default_frame = frame

    def get_telemetry(self) -> DroneTelemetry:
        self.telemetry.last_heartbeat = time.time()
        return self.telemetry

    def get_camera_frame(self) -> Optional[np.ndarray]:
        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                return frame
        return self._default_frame.copy()

    def get_guidance_command(self) -> Dict[str, Any]:
        """Gönüllü pilota gösterilecek hedef rota ve tavsiye irtifa paketi."""
        return {
            "drone_id": self.drone_id,
            "pilot_name": self.pilot_name,
            "target_heading_deg": round(self.assigned_heading, 1),
            "target_speed_ms": round(math.hypot(self.assigned_target_vx, self.assigned_target_vy), 1),
            "target_altitude_m": round(self.assigned_target_alt, 1),
            "suggested_action": "HEDEF_YÖNE_İLERLE"
        }
