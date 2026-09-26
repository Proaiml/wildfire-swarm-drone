"""
PyreSwarm - Yüksek Doğruluklu Simüle Drone (High-Fidelity Simulated Drone)
Basitleştirilmiş nokta-kütle kinematiği, batarya tükenimi ve sentetik orman/yangın kamera akışı simülatörü.
"""

import os
import time
import math
import random
from typing import Optional, List, Tuple
import numpy as np
import cv2

from hardware.drone_base import BaseDrone, DroneMode, DroneType, DroneTelemetry


class SyntheticCamera:
    """Tatbikat kamerası: gerçek bir otopilotla (ör. ArduPilot SITL) uçan araca, operatörün
    gizli tatbikat hedeflerini aşağı bakan bir kamera gibi gösterir. Yalnızca tatbikat içindir;
    görüntü üstünde "SENTETİK" etiketi bulunur, gerçek kameranın yerine geçmez."""

    def __init__(self, targets_provider):
        self.targets_provider = targets_provider      # callable -> [(lat, lon, intensity), ...]
        self.drone_id = "synthetic-camera"
        self.ASSET_DIR = SimulatedDrone.ASSET_DIR
        self.images = SimulatedDrone._load_sample_images(self)
        self.texture = SimulatedDrone._generate_forest_background(self)

    def __call__(self, telemetry, capabilities) -> Optional[np.ndarray]:
        if not telemetry.is_in_air:
            return None
        return render_synthetic_frame(telemetry.lat, telemetry.lon, telemetry.alt,
                                      capabilities.get("camera_hfov_deg", 84), self.targets_provider(),
                                      self.images, self.texture, heading_deg=getattr(telemetry, "heading", 0.0))


FIRE_EXTENT_M = 30.0   # sentetik yangının yerdeki genişliği


def render_synthetic_frame(lat, lon, alt, hfov_deg, fire_targets, images, texture, heading_deg=0.0) -> np.ndarray:
    """Aşağı bakan (nadir) kamera karesi.

    Görüş alanındaki her yangın, drone'a göre gerçek konumunda ve irtifaya göre gerçek boyutunda
    çizilir; kare drone'un burun yönüne (heading) göre döner. Böylece algılayıcının pikselden
    GPS'e dönüşümü tatbikatta da gerçekten sınanır. Hangi fotoğrafın kullanılacağı hedefin
    konumundan belirlenir (listedeki sırası değişse de aynı kalır)."""
    frame = texture.copy()
    if not images or alt <= 1.0:
        return frame
    h, w = frame.shape[:2]
    half_h = math.radians(hfov_deg) / 2.0
    half_v = math.radians(hfov_deg * h / float(w)) / 2.0
    m_per_deg_lon = SimulatedDrone.METERS_PER_DEGREE * math.cos(math.radians(lat))
    yaw = math.radians(heading_deg or 0.0)
    c, s_ = math.cos(yaw), math.sin(yaw)
    for f_lat, f_lon, _intensity in fire_targets:
        east = (f_lon - lon) * m_per_deg_lon
        north = (f_lat - lat) * SimulatedDrone.METERS_PER_DEGREE
        # dünya (doğu, kuzey) -> kamera (sağ, ileri); fire_detector'daki dönüşümün tersi
        right = c * east - s_ * north
        ahead = s_ * east + c * north
        ang_x, ang_y = math.atan2(right, alt), math.atan2(ahead, alt)
        if abs(ang_x) > half_h * 1.15 or abs(ang_y) > half_v * 1.15:
            continue
        px = int(round(w / 2 + (ang_x / half_h) * w / 2))
        py = int(round(h / 2 - (ang_y / half_v) * h / 2))
        ground_w = 2 * alt * math.tan(half_h)
        pw = max(24, int(round(FIRE_EXTENT_M / ground_w * w)))
        ph = max(18, int(round(pw * 0.75)))
        key = int(abs(f_lat * 1.0e5) + abs(f_lon * 1.0e5))
        patch = cv2.resize(images[key % len(images)], (pw, ph))
        x0, y0 = px - pw // 2, py - ph // 2
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + pw), min(h, y0 + ph)
        if xa >= xb or ya >= yb:
            continue
        frame[ya:yb, xa:xb] = patch[ya - y0:yb - y0, xa - x0:xb - x0]
    return frame


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
        battery_drain_rate_per_sec: float = 0.06, # Basit ~28 dakika hover varsayımı; üretici ölçümü değil
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
        self.target_takeoff_alt = None
        self.geofence_mgr = None
        self.aoi_bounds = None
        self.safety_hold = False

        # Gerçekçi test resimlerini yükle
        self.fire_images = self._load_sample_images()
        self.forest_texture = self._generate_forest_background()

    # Proje kökü: sunucu hangi klasörden başlatılırsa başlatılsın resimler bulunur.
    # (Önceden göreli yol kullanılıyordu; proje dışından başlatınca kamera hiç yangın görmüyordu.)
    ASSET_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _load_sample_images(self) -> List[np.ndarray]:
        """Proje kökündeki gerçek yangın/duman resimlerini önbelleğe alır."""
        imgs = []
        # smoke.png modelde (best.pt) tespit üretmiyor; tatbikat kamerası yalnızca modelin gördüğü karelerle çalışır
        for filename in ["fire.jpg", "mana.jpg"]:
            path = os.path.join(self.ASSET_DIR, filename)
            if os.path.exists(path):
                try:
                    img = cv2.imread(path)
                    if img is not None:
                        imgs.append(img)
                except Exception:
                    pass
        if not imgs:
            print(f"[{self.drone_id}] UYARI: sentetik kamera için yangın resmi bulunamadı ({self.ASSET_DIR})")
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
        self.target_takeoff_alt = target_alt
        self.mode = DroneMode.TAKEOFF
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
            self.cmd_vx = (dx_m / dist) * min(speed, dist*.5)
            self.cmd_vy = (dy_m / dist) * min(speed, dist*.5)
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

        if not self.telemetry.is_in_air:
            self.cmd_vx = self.cmd_vy = self.cmd_vz = 0.0
            self.telemetry.vx = self.telemetry.vy = self.telemetry.vz = 0.0
            self.telemetry.speed = 0.0
            self.telemetry.last_heartbeat = now
            return
        if self.mode == DroneMode.TAKEOFF:
            self.cmd_vx = self.cmd_vy = 0.0
            self.cmd_vz = min(2.0, max(0.0, self.target_takeoff_alt-self.telemetry.alt))
            if abs(self.target_takeoff_alt-self.telemetry.alt) < .5:
                self.mode = DroneMode.MISSION_PSO
                self.telemetry.mode = self.mode
        actual_dt = min(actual_dt, .5)
        dvx, dvy = self.cmd_vx-self.telemetry.vx, self.cmd_vy-self.telemetry.vy
        change = math.hypot(dvx, dvy)
        factor = min(1.0, 2.5*actual_dt/max(change, .0001))
        self.telemetry.vx += dvx*factor
        self.telemetry.vy += dvy*factor
        self.telemetry.vz += max(-2*actual_dt, min(2*actual_dt, self.cmd_vz-self.telemetry.vz))
        self.telemetry.alt = max(0.0, self.telemetry.alt+self.telemetry.vz*actual_dt)
        if self.telemetry.alt <= .1 and self.mode == DroneMode.LANDING:
            self.telemetry.alt = 0.0
            self.telemetry.is_in_air = False
            self.telemetry.is_armed = False
            self.mode = DroneMode.IDLE
            self.telemetry.mode = self.mode
            self.telemetry.vx = self.telemetry.vy = self.telemetry.vz = 0.0
            self.cmd_vx = self.cmd_vy = self.cmd_vz = 0.0
        m_per_deg_lon = self.METERS_PER_DEGREE * math.cos(math.radians(self.telemetry.lat))
        new_lon = self.telemetry.lon+self.telemetry.vx*actual_dt/m_per_deg_lon
        new_lat = self.telemetry.lat+self.telemetry.vy*actual_dt/self.METERS_PER_DEGREE
        safe = not self.geofence_mgr or self.geofence_mgr.path_is_clear(
            self.telemetry.lat, self.telemetry.lon, new_lat, new_lon, self.telemetry.alt)
        if self.aoi_bounds and self.mode == DroneMode.MISSION_PSO:
            b = self.aoi_bounds
            safe = safe and b['min_lat'] <= new_lat <= b['max_lat'] and b['min_lon'] <= new_lon <= b['max_lon']
        if not safe:
            self.safety_hold = True
        elif math.hypot(self.cmd_vx, self.cmd_vy) > .1:
            self.safety_hold = False
        if safe:
            self.telemetry.lat, self.telemetry.lon = new_lat, new_lon
        else:
            # Simulation containment, NOT a physical emergency-braking guarantee.
            self.telemetry.vx = self.telemetry.vy = 0.0
            self.cmd_vx = self.cmd_vy = 0.0

        # Yer hızı ve heading
        self.telemetry.speed = math.hypot(self.telemetry.vx, self.telemetry.vy)
        if self.telemetry.speed > 0.3:
            self.telemetry.heading = (math.degrees(math.atan2(self.telemetry.vx, self.telemetry.vy)) + 360.0) % 360.0

        # Batarya tükenimi ve saha emniyet denetimi (Fail-Safe)
        if self.telemetry.is_in_air:
            self.telemetry.battery_percentage = max(
                0.0, self.telemetry.battery_percentage - (self.battery_drain_rate * actual_dt * (1 + .025*self.telemetry.speed + .1*max(0,self.telemetry.vz)))
            )
            if self.telemetry.battery_percentage <= 20.0:
                self.telemetry.is_low_battery = True
            else:
                self.telemetry.is_low_battery = False

            # Sahada batarya %15 altına düşerse acil otonom RTL tetikle
            distance_home = math.hypot((self.home_lat-self.telemetry.lat)*self.METERS_PER_DEGREE,
                                       (self.home_lon-self.telemetry.lon)*m_per_deg_lon)
            return_seconds = distance_home/max(1,min(10,self.capabilities['max_speed_ms'])) + self.telemetry.alt/2 + 20
            reserve = max(15.0, 10.0 + return_seconds*self.battery_drain_rate*1.5)
            if self.telemetry.battery_percentage <= reserve and self.mode in (DroneMode.MISSION_PSO, DroneMode.TAKEOFF, DroneMode.ARMED):
                self.return_to_launch()

        self.telemetry.last_heartbeat = now

    def get_telemetry(self) -> DroneTelemetry:
        return self.telemetry

    def get_camera_frame(self, pose=None) -> Optional[np.ndarray]:
        """
        Drone'un konumuna göre kamera görüntüsü üretir. pose verilirse kare tam o telemetri
        kopyasından çizilir: algılayıcı aynı pozla GPS'e çevirir (dönüşte heading ters dönse bile).
        """
        t = pose or self.telemetry
        return render_synthetic_frame(t.lat, t.lon, t.alt,
                                      self.capabilities["camera_hfov_deg"], self.fire_targets,
                                      self.fire_images, self.forest_texture, heading_deg=t.heading)
