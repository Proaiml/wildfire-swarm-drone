"""
PyreSwarm - Bağlantı Kaybı ve Sağlık Yönetimi (Communication Loss & Health Failsafe)
Drone bağlantı kesintilerini izler: CONNECTED -> DEGRADED -> STALE -> DISCONNECTED -> RECOVERING
Sürü optimizasyonunun kesintiye uğrayan drone yüzünden çökmesini veya tıkanmasını önler.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
import time


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"       # Kalp atışı < 3.0 sn
    DEGRADED = "DEGRADED"         # 3.0 sn <= Kalp atışı < 7.0 sn (Gecikmeli/paket kaybı)
    STALE = "STALE"               # 7.0 sn <= Kalp atışı < 15.0 sn (Kritik bayatlık)
    DISCONNECTED = "DISCONNECTED" # >= 15.0 sn (Bağlantı koptu, görevden düşürülmeli)
    RECOVERING = "RECOVERING"     # Yeniden bağlandı, durum doğrulaması yapılıyor


@dataclass
class DroneLinkState:
    drone_id: str
    status: ConnectionStatus = ConnectionStatus.CONNECTED
    last_heartbeat: float = field(default_factory=time.time)
    last_lat: float = 0.0
    last_lon: float = 0.0
    last_alt: float = 0.0
    last_battery: float = 100.0
    disconnect_count: int = 0


class CommunicationLossHandler:
    """
    Sürüdeki her bir drone'un haberleşme link kalitesini denetleyen bekçi (watchdog).
    """

    def __init__(
        self,
        degraded_threshold_sec: float = 3.0,
        stale_threshold_sec: float = 7.0,
        disconnected_threshold_sec: float = 15.0
    ):
        self.t_degraded = degraded_threshold_sec
        self.t_stale = stale_threshold_sec
        self.t_disconnected = disconnected_threshold_sec

        self._links: Dict[str, DroneLinkState] = {}
        self._listeners: List[Callable[[str, ConnectionStatus, ConnectionStatus], None]] = []

    def register_drone(self, drone_id: str):
        if drone_id not in self._links:
            self._links[drone_id] = DroneLinkState(drone_id=drone_id)

    def record_heartbeat(self, drone_id: str, lat: float = 0.0, lon: float = 0.0, alt: float = 0.0, battery: float = 100.0):
        """Drone'dan gelen yeni kalp atışını ve telemetriyi kaydeder."""
        now = time.time()
        if drone_id not in self._links:
            self.register_drone(drone_id)

        link = self._links[drone_id]
        old_status = link.status

        link.last_heartbeat = now
        link.last_lat = lat
        link.last_lon = lon
        link.last_alt = alt
        link.last_battery = battery

        if old_status in (ConnectionStatus.DISCONNECTED, ConnectionStatus.STALE):
            link.status = ConnectionStatus.RECOVERING
            self._notify_status_change(drone_id, old_status, ConnectionStatus.RECOVERING)
            link.status = ConnectionStatus.CONNECTED
            self._notify_status_change(drone_id, ConnectionStatus.RECOVERING, ConnectionStatus.CONNECTED)
        elif old_status == ConnectionStatus.DEGRADED:
            link.status = ConnectionStatus.CONNECTED
            self._notify_status_change(drone_id, old_status, ConnectionStatus.CONNECTED)

    def audit_all_links(self, current_time: Optional[float] = None) -> Dict[str, ConnectionStatus]:
        """Tüm drone'ların kalp atışlarını tarar ve durumlarını günceller."""
        now = current_time or time.time()
        results = {}

        for drone_id, link in self._links.items():
            dt = now - link.last_heartbeat
            old_status = link.status

            if dt >= self.t_disconnected:
                new_status = ConnectionStatus.DISCONNECTED
            elif dt >= self.t_stale:
                new_status = ConnectionStatus.STALE
            elif dt >= self.t_degraded:
                new_status = ConnectionStatus.DEGRADED
            else:
                new_status = ConnectionStatus.CONNECTED

            if new_status != old_status:
                if new_status == ConnectionStatus.DISCONNECTED and old_status != ConnectionStatus.DISCONNECTED:
                    link.disconnect_count += 1
                link.status = new_status
                self._notify_status_change(drone_id, old_status, new_status)

            results[drone_id] = link.status

        return results

    def add_status_listener(self, callback: Callable[[str, ConnectionStatus, ConnectionStatus], None]):
        self._listeners.append(callback)

    def _notify_status_change(self, drone_id: str, old_status: ConnectionStatus, new_status: ConnectionStatus):
        for listener in self._listeners:
            try:
                listener(drone_id, old_status, new_status)
            except Exception as e:
                print(f"[LossHandler] Listener hatası: {e}")

    def get_status(self, drone_id: str) -> ConnectionStatus:
        if drone_id in self._links:
            return self._links[drone_id].status
        return ConnectionStatus.DISCONNECTED

    def get_disconnected_drones(self) -> List[str]:
        return [
            d_id for d_id, link in self._links.items()
            if link.status == ConnectionStatus.DISCONNECTED
        ]
