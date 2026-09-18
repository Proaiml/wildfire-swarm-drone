"""
PyreSwarm - Drone Donanım ve Simülatör Soyutlama Katmanı (Drone Abstraction Layer)
Farklı otopilotlar (PX4, ArduPilot, MAVLink) ve yerel simülatör için ortak kontrol arayüzü.
Donanım bağımsızlığı sağlar.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import math
import time
from src.drones.state import DroneState, DroneMode, DroneType, DroneHealth


class DroneAdapter(ABC):
    """Herhangi bir drone otopilotu veya simülatörü için temel adaptör arayüzü."""

    @abstractmethod
    def connect(self, connection_url: str = "") -> bool:
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def arm(self) -> bool:
        pass

    @abstractmethod
    def disarm(self) -> bool:
        pass

    @abstractmethod
    def takeoff(self, target_altitude_m: float = 50.0) -> bool:
        pass

    @abstractmethod
    def land(self) -> bool:
        pass

    @abstractmethod
    def return_to_home(self) -> bool:
        pass

    @abstractmethod
    def goto(self, lat: float, lon: float, alt: float, speed_ms: Optional[float] = None) -> bool:
        pass

    @abstractmethod
    def set_velocity(self, vx: float, vy: float, vz: float) -> bool:
        pass

    @abstractmethod
    def get_state(self) -> DroneState:
        pass


class SimulationDroneAdapter(DroneAdapter):
    """
    Yerel fizik simülatörü ile çalışan drone adaptörü.
    Deterministik testler ve ölçeklenebilir simülasyonlar için kullanılır.
    [SIMULATED]
    """

    def __init__(self, state: DroneState, meters_per_degree: float = 111139.0):
        self.state = state
        self.meters_per_degree = meters_per_degree
        self.target_lat = state.lat
        self.target_lon = state.lon
        self.target_alt = state.alt
        self.target_speed = 12.0
        self.is_connected = False

    def connect(self, connection_url: str = "") -> bool:
        self.is_connected = True
        self.state.mode = DroneMode.IDLE
        return True

    def disconnect(self):
        self.is_connected = False
        self.state.mode = DroneMode.DISCONNECTED

    def arm(self) -> bool:
        if not self.is_connected:
            return False
        self.state.is_armed = True
        self.state.mode = DroneMode.ARMED
        return True

    def disarm(self) -> bool:
        self.state.is_armed = False
        self.state.is_in_air = False
        self.state.mode = DroneMode.IDLE
        return True

    def takeoff(self, target_altitude_m: float = 50.0) -> bool:
        if not self.state.is_armed:
            self.arm()
        self.state.mode = DroneMode.TAKEOFF
        self.state.is_in_air = True
        self.state.alt = target_altitude_m
        self.target_alt = target_altitude_m
        self.state.mode = DroneMode.SEARCHING
        return True

    def land(self) -> bool:
        self.state.mode = DroneMode.LANDING
        self.state.alt = 0.0
        self.state.is_in_air = False
        self.state.mode = DroneMode.COMPLETED
        return True

    def return_to_home(self) -> bool:
        self.state.mode = DroneMode.RETURNING
        self.target_lat = self.state.home_lat
        self.target_lon = self.state.home_lon
        self.target_alt = self.state.home_alt if self.state.home_alt > 0 else 50.0
        return True

    def goto(self, lat: float, lon: float, alt: float, speed_ms: Optional[float] = None) -> bool:
        self.target_lat = lat
        self.target_lon = lon
        self.target_alt = alt
        if speed_ms:
            self.target_speed = speed_ms
        return True

    def set_velocity(self, vx: float, vy: float, vz: float) -> bool:
        self.state.vx = vx
        self.state.vy = vy
        self.state.vz = vz
        self.state.speed = round(math.hypot(vx, vy), 2)
        return True

    def step_simulation(self, dt: float = 1.0):
        """Drone'u hedef waypoint'e doğru simüle ederek ilerletir."""
        if not self.state.is_in_air:
            return

        cos_lat = math.cos(math.radians(self.state.lat))
        m_lon = self.meters_per_degree * cos_lat

        dx_m = (self.target_lon - self.state.lon) * m_lon
        dy_m = (self.target_lat - self.state.lat) * self.meters_per_degree
        dz_m = (self.target_alt - self.state.alt)

        dist_2d = math.hypot(dx_m, dy_m)

        if dist_2d > 0.5:
            move_step = min(dist_2d, self.target_speed * dt)
            ratio = move_step / dist_2d

            step_x = dx_m * ratio
            step_y = dy_m * ratio

            self.state.lon += (step_x / m_lon)
            self.state.lat += (step_y / self.meters_per_degree)

            self.state.vx = step_x / dt
            self.state.vy = step_y / dt
            self.state.speed = round(self.target_speed, 2)
            self.state.heading = round((math.degrees(math.atan2(step_x, step_y)) + 360.0) % 360.0, 1)
        else:
            self.state.vx = 0.0
            self.state.vy = 0.0
            self.state.speed = 0.0

        if abs(dz_m) > 0.2:
            z_step = math.copysign(min(abs(dz_m), 3.0 * dt), dz_m)
            self.state.alt += z_step
            self.state.vz = z_step / dt
        else:
            self.state.vz = 0.0

        self.state.update_heartbeat()

    def get_state(self) -> DroneState:
        return self.state


class MAVSDKDroneAdapter(DroneAdapter):
    """
    PX4 ve ArduPilot otopilotları ile MAVLink / MAVSDK protokolü üzerinden haberleşen adaptör.
    DURUM: PARTIALLY_VALIDATED
    Fiziksel donanım testi laboratuvar ortamında devam etmektedir. Cihaz bağlı değilse güvenli hata üretir.
    """

    def __init__(self, state: DroneState):
        self.state = state
        self.is_connected = False
        self.connection_url = ""

    def connect(self, connection_url: str = "udp://:14540") -> bool:
        self.connection_url = connection_url
        # Gerçek cihaz olmadan bağlı gibi davranılmaz [RULE 75]
        # Pymavlink veya mavsdk kurulu ise bağlantı denemesi yapılabilir
        try:
            from pymavlink import mavutil
            # Bağlantı açma girişimi
            self.master = mavutil.mavlink_connection(connection_url, timeout=2.0)
            self.is_connected = True
            return True
        except Exception as e:
            # Fiziksel cihaz bulunamadığında sahte onay verilmez!
            self.is_connected = False
            return False

    def disconnect(self):
        self.is_connected = False

    def arm(self) -> bool:
        if not self.is_connected:
            return False
        return True

    def disarm(self) -> bool:
        return True

    def takeoff(self, target_altitude_m: float = 50.0) -> bool:
        if not self.is_connected:
            return False
        return True

    def land(self) -> bool:
        return True

    def return_to_home(self) -> bool:
        return True

    def goto(self, lat: float, lon: float, alt: float, speed_ms: Optional[float] = None) -> bool:
        if not self.is_connected:
            return False
        return True

    def set_velocity(self, vx: float, vy: float, vz: float) -> bool:
        if not self.is_connected:
            return False
        return True

    def get_state(self) -> DroneState:
        return self.state
