"""
PyreSwarm - Yüksek Doğruluklu Simüle Drone (High-Fidelity Simulated Drone)
6-DOF kinematik, batarya tükenimi ve sentetik orman/yangın kamera akışı simülatörü.
"""

import os
import time
import math
import random
from typing import Optional, List, Tuple
import numpy as np
import cv2

from hardware.drone_base import BaseDrone, DroneMode, DroneType, DroneTelemetry


class SimulatedDrone(BaseDrone):
    """
    Yazılım testleri ve görselleştirme için gerçekçi drone simülatörü.
    """

    METERS_PER_DEGREE = 111139.0

    def __init__(
        self,
        drone_id: str,
        initial_lat: float,
        initial_lon: float,
        initial_alt: float = 0.0,
        battery_drain_rate_per_sec: float = 0.02, # ~80 dakikalık uçuş süresi
        fire_targets: Optional[List[Tuple[float, float, float]]] = None # [(lat, lon, intensity), ...]
    ):
        super().__init__(drone_id=drone_id, drone_type=DroneType.SIMULATED)
        self.home_lat = initial_lat
        self.home_lon = initial_lon
        self.home_alt = initial_alt

        self.telemetry.lat = initial_lat
        self.telemetry.lon = initial_lon
        self.telemetry.alt = initial_alt
        self.telemetry.battery_percentage = 100.0

        self.fire_targets = fire_targets or []
        self.battery_drain_rate = battery_drain_rate_per_sec
        self.last_update_time = time.time()

        # Hedef hızlar
        self.cmd_vx = 0.0
        self.cmd_vy = 0.0
        self.cmd_vz = 0.0

        # Gerçekçi test resimlerini yükle
        self.fire_images = self._load_sample_images()
        self.forest_texture = self._generate_forest_background()

    def _load_sample_images(self) -> List[np.ndarray]:
        """Çalışma dizinindeki gerçek yangın/duman resimlerini önbelleğe alır."""
        imgs = []
        for filename in ["fire.jpg", "mana.jpg", "smoke.png"]:
            if os.path.exists(filename):
                try:
                    img = cv2.imread(filename)
                    if img is not None:
                        imgs.append(img)
                except Exception:
                    pass
        return imgs

    def _generate_forest_background(self) -> np.ndarray:
        """Kamera yangın görmüyorken gösterilecek sentetik orman/doğa zemini karesi."""
        h, w = 480, 640
        # Yeşil ve kahve tonlarında doğal orman dokusu
        bg = np.zeros((h, w, 3), dtype=np.uint8)
        bg[:, :] = (28, 70, 35)  # Koyu yeşil orman
        # Doğal gürültü / doku
        noise = np.random.randint(-15, 15, (h, w, 3), dtype=np.int16)
        bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return bg

    def connect(self) -> bool:
        self.mode = DroneMode.ARMED
        self.telemetry.mode = self.mode
        self.telemetry.is_armed = True
        return True

    def disconnect(self):
        self.mode = DroneMode.DISCONNECTED
        self.telemetry.mode = self.mode
        self.telemetry.is_armed = False

    def arm(self) -> bool:
        self.telemetry.is_armed = True
        self.mode = DroneMode.ARMED
        self.telemetry.mode = self.mode
        return True

    def disarm(self) -> bool:
        self.telemetry.is_armed = False
        self.mode = DroneMode.IDLE
        self.telemetry.mode = self.mode
        return True

    def takeoff(self, target_alt: float = 30.0) -> bool:
        self.telemetry.is_armed = True
        self.telemetry.is_in_air = True
        self.telemetry.alt = target_alt
        self.mode = DroneMode.MISSION_PSO
        self.telemetry.mode = self.mode
        return True

    def land(self) -> bool:
        self.cmd_vx = 0.0
        self.cmd_vy = 0.0
        self.cmd_vz = -2.0
        self.mode = DroneMode.LANDING
        self.telemetry.mode = self.mode
        return True

    def return_to_launch(self) -> bool:
        self.mode = DroneMode.RTL
        self.telemetry.mode = self.mode
        return True

    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        self.cmd_vx = vx
        self.cmd_vy = vy
        self.cmd_vz = vz
        return True

    def goto_coordinate(self, lat: float, lon: float, alt: float, speed: float = 8.0) -> bool:
        cos_lat = math.cos(math.radians(self.telemetry.lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        dx_m = (lon - self.telemetry.lon) * m_per_deg_lon
        dy_m = (lat - self.telemetry.lat) * self.METERS_PER_DEGREE
        dz_m = alt - self.telemetry.alt

        dist = math.hypot(dx_m, dy_m)
        if dist > 1.0:
            self.cmd_vx = (dx_m / dist) * speed
            self.cmd_vy = (dy_m / dist) * speed
        else:
            self.cmd_vx = 0.0
            self.cmd_vy = 0.0

        self.cmd_vz = max(-3.0, min(3.0, dz_m))
        return True

    def update_physics(self, dt: float = 0.5):
        """Kinematik durum güncellemesi (Euler Entegratörü)."""
        now = time.time()
        actual_dt = min(1.0, max(0.01, now - self.last_update_time)) if dt <= 0 else dt
        self.last_update_time = now

        # RTL (Return To Launch) kontrolü
        if self.mode == DroneMode.RTL:
            self.goto_coordinate(self.home_lat, self.home_lon, 30.0, speed=10.0)
            cos_lat = math.cos(math.radians(self.telemetry.lat))
            m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat
            dx = (self.home_lon - self.telemetry.lon) * m_per_deg_lon
            dy = (self.home_lat - self.telemetry.lat) * self.METERS_PER_DEGREE
            if math.hypot(dx, dy) < 5.0:
                self.land()

        # Yumuşak ivmelenme (Atalet filtresi)
        alpha = 0.6
        self.telemetry.vx = alpha * self.cmd_vx + (1 - alpha) * self.telemetry.vx
        self.telemetry.vy = alpha * self.cmd_vy + (1 - alpha) * self.telemetry.vy
        self.telemetry.vz = alpha * self.cmd_vz + (1 - alpha) * self.telemetry.vz

        # İrtifa güncelleme
        self.telemetry.alt = max(0.0, self.telemetry.alt + self.telemetry.vz * actual_dt)
        if self.telemetry.alt <= 0.5 and self.mode == DroneMode.LANDING:
            self.telemetry.alt = 0.0
            self.telemetry.is_in_air = False
            self.telemetry.is_armed = False
            self.mode = DroneMode.IDLE
            self.telemetry.mode = self.mode

        # GPS güncelleme
        cos_lat = math.cos(math.radians(self.telemetry.lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        self.telemetry.lon += (self.telemetry.vx * actual_dt) / m_per_deg_lon
        self.telemetry.lat += (self.telemetry.vy * actual_dt) / self.METERS_PER_DEGREE

        # Yer hızı ve heading
        self.telemetry.speed = math.hypot(self.telemetry.vx, self.telemetry.vy)
        if self.telemetry.speed > 0.3:
            self.telemetry.heading = (math.degrees(math.atan2(self.telemetry.vx, self.telemetry.vy)) + 360.0) % 360.0

        # Batarya tükenimi ve saha emniyet denetimi (Fail-Safe)
        if self.telemetry.is_in_air:
            self.telemetry.battery_percentage = max(
                0.0, self.telemetry.battery_percentage - (self.battery_drain_rate * actual_dt)
            )
            if self.telemetry.battery_percentage <= 20.0:
                self.telemetry.is_low_battery = True
            else:
                self.telemetry.is_low_battery = False

            # Sahada batarya %15 altına düşerse acil otonom RTL tetikle
            if self.telemetry.battery_percentage <= 15.0 and self.mode == DroneMode.MISSION_PSO:
                self.return_to_launch()

        self.telemetry.last_heartbeat = now

    def get_telemetry(self) -> DroneTelemetry:
        return self.telemetry

    def get_camera_frame(self) -> Optional[np.ndarray]:
        """
        Drone'un anlık konumuna göre kamera görüntüsü üretir.
        Eğer bir yangın odağının üzerindeyse/yakınındaysa gerçek yangın resmini döndürür.
        """
        cos_lat = math.cos(math.radians(self.telemetry.lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        # En yakın yangın odağını bul
        closest_dist = 999999.0
        closest_intensity = 0.0

        for f_lat, f_lon, intensity in self.fire_targets:
            dx = (self.telemetry.lon - f_lon) * m_per_deg_lon
            dy = (self.telemetry.lat - f_lat) * self.METERS_PER_DEGREE
            dist = math.hypot(dx, dy)
            if dist < closest_dist:
                closest_dist = dist
                closest_intensity = intensity

        # Görüş Alanı (FOV) yarıçapı irtifaya bağlıdır: R = Alt * tan(FOV/2)
        fov_radius = max(20.0, self.telemetry.alt * 0.9)

        if closest_dist < fov_radius and len(self.fire_images) > 0:
            # Yangın görüş alanında!
            # Resimlerden birini seç ve mesafeye göre harmanla
            img_idx = int(hash(self.drone_id)) % len(self.fire_images)
            fire_img = self.fire_images[img_idx].copy()

            # 640x480 boyutuna getir
            fire_img = cv2.resize(fire_img, (640, 480))

            # Merkeze olan uzaklığa göre karıştır
            blend_ratio = max(0.2, min(1.0, 1.0 - (closest_dist / fov_radius)))
            frame = cv2.addWeighted(fire_img, blend_ratio, self.forest_texture, 1.0 - blend_ratio, 0)
            return frame
        else:
            # Yangın yok, sadece orman zemini
            return self.forest_texture.copy()
