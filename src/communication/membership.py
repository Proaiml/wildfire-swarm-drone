"""
PyreSwarm - Dinamik Sürü Üyeliği ve Yetenek Keşfi (Dynamic Swarm Join & Capability Discovery)
Çalışma zamanında yeni bir drone katıldığında (örneğin gönüllü sivil drone veya yedek filo):
JOIN_REQUEST -> Kimlik Doğrulama -> Yetenek Keşfi -> Sağlık/Batarya Onayı -> Sürü Kaydı -> İlk Görev Ataması
akışını kesintisiz yürütür.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Tuple, Any
import time
from src.drones.state import DroneState, DroneMode, DroneType, DroneHealth


@dataclass
class DroneCapabilities:
    """Yeni katılan drone'un donanım ve algılama kabiliyetleri."""
    drone_id: str
    drone_type: str = "SIMULATED"
    max_speed_ms: float = 15.0
    cruise_speed_ms: float = 12.0
    max_altitude_m: float = 120.0
    battery_remaining_pct: float = 100.0
    estimated_flight_time_min: float = 25.0
    camera_resolution: Tuple[int, int] = (1920, 1080)
    camera_fov_deg: float = 84.0
    has_thermal_camera: bool = False
    gps_accuracy_m: float = 1.5
    compute_capability: str = "EDGE_CPU"   # EDGE_CPU, JETSON_GPU, CLOUD_RELAY
    autopilot_type: str = "PX4_MAVLINK"    # PX4_MAVLINK, ARDUPILOT, DJI_SDK, MOCK


class SwarmMembershipManager:
    """
    Sürüye katılım isteklerini doğrulayan, yetenek envanterini çıkaran ve sürüye kaydeden yönetici.
    """

    def __init__(self, auth_token_secret: str = "PYRESWARM_AUTH_TOKEN_2026"):
        self.secret = auth_token_secret
        # drone_id -> DroneCapabilities
        self._capabilities: Dict[str, DroneCapabilities] = {}
        # drone_id -> DroneState
        self._active_members: Dict[str, DroneState] = {}

    def process_join_request(
        self,
        caps: DroneCapabilities,
        initial_lat: float,
        initial_lon: float,
        initial_alt: float = 0.0,
        auth_token: str = "PYRESWARM_AUTH_TOKEN_2026"
    ) -> Tuple[bool, str, Optional[DroneState]]:
        """
        Gelen katılım isteğini doğrular ve sürüye kaydeder.
        Döndürür: (success, reason_message, created_drone_state)
        """
        # 1. Kimlik ve Token Doğrulaması
        if auth_token != self.secret:
            return False, "AUTHENTICATION_FAILED: Geçersiz sürü katılım belirteci (token).", None

        # 2. Yinelenen Kayıt (Duplicate Registration) Kontrolü
        if caps.drone_id in self._active_members:
            return False, f"DUPLICATE_ID: '{caps.drone_id}' kimlikli drone zaten sürüye kayıtlı!", None

        # 3. Asgari Sağlık ve Batarya Doğrulaması
        if caps.battery_remaining_pct < 25.0:
            return False, f"INSUFFICIENT_BATTERY: Katılım için en az %25 batarya gerekir (Mevcut: %{caps.battery_remaining_pct})", None

        if caps.cruise_speed_ms <= 0 or caps.max_speed_ms <= 0:
            return False, "INVALID_DYNAMICS: Hız parametreleri pozitif olmalıdır.", None

        # 4. Yetenek Kaydı
        self._capabilities[caps.drone_id] = caps

        # 5. Yeni DroneState Oluşturma
        d_type = DroneType.SIMULATED
        if "mavlink" in caps.autopilot_type.lower():
            d_type = DroneType.MAVLINK
        elif "dji" in caps.autopilot_type.lower():
            d_type = DroneType.DJI

        new_drone = DroneState(
            drone_id=caps.drone_id,
            drone_type=d_type,
            lat=initial_lat,
            lon=initial_lon,
            alt=initial_alt,
            battery_percentage=caps.battery_remaining_pct,
            battery_voltage=round(13.6 + (16.8 - 13.6) * (caps.battery_remaining_pct / 100.0), 2),
            home_lat=initial_lat,
            home_lon=initial_lon,
            home_alt=initial_alt,
            mode=DroneMode.IDLE,
            health=DroneHealth.HEALTHY,
            is_armed=False,
            is_in_air=False
        )

        self._active_members[caps.drone_id] = new_drone
        return True, f"SUCCESS: '{caps.drone_id}' sürüye başarıyla entegre edildi.", new_drone

    def leave_swarm(self, drone_id: str, reason: str = "NORMAL_EXIT") -> bool:
        """Drone'u sürü kaydından güvenli biçimde çıkarır."""
        if drone_id in self._active_members:
            del self._active_members[drone_id]
            if drone_id in self._capabilities:
                del self._capabilities[drone_id]
            return True
        return False

    def get_member(self, drone_id: str) -> Optional[DroneState]:
        return self._active_members.get(drone_id)

    def get_capabilities(self, drone_id: str) -> Optional[DroneCapabilities]:
        return self._capabilities.get(drone_id)

    def get_all_members(self) -> Dict[str, DroneState]:
        return self._active_members
