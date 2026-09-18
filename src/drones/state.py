"""
PyreSwarm - Drone Durum Modeli ve Tip Tanımları (Drone State Model)
Dağıtık sürü düğümleri için versiyonlanmış, tip güvenli, ENU ve WGS84 destekli durum yapısı.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Tuple, Optional, Dict, Any
import time


class DroneMode(str, Enum):
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    ARMED = "ARMED"
    TAKEOFF = "TAKEOFF"
    SEARCHING = "SEARCHING"           # PSO Arama Modu
    VERIFYING = "VERIFYING"           # Yangın İnceleme / Alçalış Modu
    MONITORING = "MONITORING"         # Doğrulanmış Yangın Çevresinde Gözlem Modu
    PATROL = "PATROL"                 # Hat / Sınır Devriye Modu
    RETURNING = "RETURNING"           # Return to Launch (RTL) Modu
    LANDING = "LANDING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    EMERGENCY = "EMERGENCY"
    DISCONNECTED = "DISCONNECTED"


class DroneType(str, Enum):
    SIMULATED = "SIMULATED"           # 6-DOF Fizik ve Sentetik Kamera
    MAVLINK = "MAVLINK"               # Pixhawk / PX4 / ArduPilot Otopilot (PARTIALLY_VALIDATED)
    DJI = "DJI"                       # DJI SDK (PARTIALLY_VALIDATED)
    VOLUNTEER = "VOLUNTEER"           # Sivil / Gönüllü Drone (Web/REST Köprüsü)


class DroneHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL_BATTERY = "CRITICAL_BATTERY"
    GPS_LOSS = "GPS_LOSS"
    CAMERA_FAILURE = "CAMERA_FAILURE"
    COMM_LOSS = "COMM_LOSS"


@dataclass
class DroneState:
    """
    Sürüdeki her bir drone için merkezi ve versiyonlanmış durum nesnesi.
    """
    drone_id: str
    drone_type: DroneType = DroneType.SIMULATED

    # Küresel WGS84 Konumu
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0                  # metre (AGL - Yerden yükseklik)

    # Yerel Metrik ENU Konumu (Üs referansına göre) [THEORETICAL_BOUND]
    local_x: float = 0.0              # Doğu (metre)
    local_y: float = 0.0              # Kuzey (metre)
    local_z: float = 0.0              # Yukarı (metre)

    # Hız Vektörü (m/s)
    vx: float = 0.0                   # Doğu hızı
    vy: float = 0.0                   # Kuzey hızı
    vz: float = 0.0                   # Dikey hız
    speed: float = 0.0                # Bileşke yer hızı
    heading: float = 0.0              # Pusula yönü (0 - 360 derece)

    # Enerji ve Güç Durumu [MANUFACTURER_SPEC / SIMULATED]
    battery_percentage: float = 100.0 # 0.0 - 100.0 %
    battery_voltage: float = 16.8     # Volt (4S LiPo varsayılanı)
    is_low_battery: bool = False      # <= 20%
    is_critical_battery: bool = False # <= 15% (Otonom RTL gerektirir)

    # Seyrüsefer ve Donanım Sağlığı
    gps_fix: bool = True
    gps_satellites: int = 14
    network_quality: int = 100        # % (Sinyal kalitesi / RSSI)
    health: DroneHealth = DroneHealth.HEALTHY
    mode: DroneMode = DroneMode.IDLE
    is_armed: bool = False
    is_in_air: bool = False

    # Yangın Algılama Kanıtları [MEASURED / SIMULATED]
    fire_confidence: float = 0.0
    smoke_confidence: float = 0.0
    current_score: float = 0.0
    detections_count: int = 0
    last_detection_timestamp: float = 0.0

    # PSO Optimizasyon Durumu
    pbest_lat: float = 0.0
    pbest_lon: float = 0.0
    pbest_alt: float = 50.0
    pbest_score: float = 0.0
    assigned_target_lat: Optional[float] = None
    assigned_target_lon: Optional[float] = None
    assigned_target_alt: Optional[float] = None

    # Operasyon ve Zaman Bilgisi
    home_lat: float = 0.0
    home_lon: float = 0.0
    home_alt: float = 0.0
    joined_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    state_version: int = 1

    def update_heartbeat(self):
        """Kalp atışı ve versiyon güncellemesi."""
        self.last_heartbeat = time.time()
        self.state_version += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serileştirilebilir sözlük çıktısı."""
        d = asdict(self)
        d["mode"] = self.mode.value
        d["drone_type"] = self.drone_type.value
        d["health"] = self.health.value
        return d
