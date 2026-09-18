"""
PyreSwarm - Donanım Soyutlama Katmanı (Hardware Abstraction Layer)
Tüm fiziksel (MAVLink, DJI) ve simüle drone'lar için ortak temel sınıf.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple
import numpy as np


class DroneMode(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    IDLE = "IDLE"
    ARMED = "ARMED"
    TAKEOFF = "TAKEOFF"
    IN_FLIGHT = "IN_FLIGHT"
    MISSION_PSO = "MISSION_PSO"
    RTL = "RTL"
    LANDING = "LANDING"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class DroneType(str, Enum):
    SIMULATED = "SIMULATED"           # Dahili Yüksek Doğruluklu Fizik Simülatörü
    MAVLINK = "MAVLINK"               # Pixhawk / PX4 / ArduPilot Otopilot
    DJI = "DJI"                       # DJI Mobile / Onboard SDK
    VOLUNTEER = "VOLUNTEER"           # Vatandaş / Gönüllü Drone (Web/REST/RTSP)


@dataclass
class DroneTelemetry:
    drone_id: str
    drone_type: DroneType
    mode: DroneMode
    lat: float
    lon: float
    alt: float                        # Yerden yükseklik / AGL (metre)
    vx: float = 0.0                   # m/s Doğu
    vy: float = 0.0                   # m/s Kuzey
    vz: float = 0.0                   # m/s Dikey
    speed: float = 0.0                # Bileşke yer hızı (m/s)
    heading: float = 0.0              # Derece (0 - 360)
    battery_percentage: float = 100.0 # 0.0 - 100.0 %
    signal_strength: int = 100        # % RSSI
    gps_satellites: int = 14          # GPS Uydu Sayısı
    current_fire_score: float = 0.0   # Anlık yangın tespit puanı
    pbest_score: float = 0.0          # Drone'un kişisel en iyi skoru
    detections_count: int = 0         # Toplam onaylanan tespit
    is_armed: bool = False
    is_in_air: bool = False
    last_heartbeat: float = 0.0


class BaseDrone(ABC):
    """
    Sürüdeki her bir drone için standart kontrol arayüzü.
    """

    def __init__(self, drone_id: str, drone_type: DroneType):
        self.drone_id = drone_id
        self.drone_type = drone_type
        self.mode = DroneMode.IDLE
        self.telemetry = DroneTelemetry(
            drone_id=drone_id,
            drone_type=drone_type,
            mode=self.mode,
            lat=0.0,
            lon=0.0,
            alt=0.0
        )

    @abstractmethod
    def connect(self) -> bool:
        """Drone otopilotuna veya simülatöre bağlanır."""
        pass

    @abstractmethod
    def disconnect(self):
        """Bağlantıyı sonlandırır."""
        pass

    @abstractmethod
    def arm(self) -> bool:
        """Motorları kollar (Arm)."""
        pass

    @abstractmethod
    def disarm(self) -> bool:
        """Motorları durdurur (Disarm)."""
        pass

    @abstractmethod
    def takeoff(self, target_alt: float = 30.0) -> bool:
        """Hedef irtifaya otonom kalkış yapar."""
        pass

    @abstractmethod
    def land(self) -> bool:
        """Olduğu yere emniyetli iniş yapar."""
        pass

    @abstractmethod
    def return_to_launch(self) -> bool:
        """Kalkış noktasına geri döner (RTL)."""
        pass

    @abstractmethod
    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        """
        PSO motorundan gelen hız vektörlerini (m/s) otopilota aktarır.
        """
        pass

    @abstractmethod
    def goto_coordinate(self, lat: float, lon: float, alt: float, speed: float = 8.0) -> bool:
        """Belirli bir GPS koordinatına yönlendirir."""
        pass

    @abstractmethod
    def get_telemetry(self) -> DroneTelemetry:
        """En güncel telemetri paketini döndürür."""
        pass

    @abstractmethod
    def get_camera_frame(self) -> Optional[np.ndarray]:
        """Kameradan anlık video karesini (OpenCV BGR formatı) çeker."""
        pass
