"""
PyreSwarm - Sürü Yönetim ve Koordinasyon Merkezi (Swarm Manager)
Tüm drone'ların, PSO motorunun, YOLO tespit katmanının ve coğrafi kısıtların entegre yönetimi.
"""

import time
import math
import threading
import uuid
import copy
from shapely.geometry import Point
from functools import wraps

def synchronized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call

from typing import List, Dict, Tuple, Optional, Any
import numpy as np

from core.geofence_manager import GeofenceManager, ZoneType
from core.fire_detector import FireDetector, DetectionResult
from core.pso_engine import PSOEngine, PSOConfig
from hardware.drone_base import BaseDrone, DroneMode, DroneType, DroneTelemetry
from hardware.simulated_drone import SimulatedDrone
from hardware.mavlink_drone import MAVLinkDrone
from hardware.volunteer_bridge import VolunteerDrone


def hub_controls(drone: BaseDrone) -> bool:
    """Hub bu drone'a hareket komutu verebilir mi?
    Simülasyon: evet. MAVLink: yalnızca operatör kontrolü verdiyse ve bağlantı canlıysa.
    Gönüllü köprüsü: hayır (yalnızca pilot rehberliği)."""
    if isinstance(drone, SimulatedDrone):
        return True
    if isinstance(drone, MAVLinkDrone):
        return drone.control_enabled and drone.link_ok()
    return False


class SwarmManager:
    """
    Sürü Drone Orkestrasyon Merkezi.
    PSO döngüsünü, YOLO algılamasını, dinamik katılımları ve kısıtları senkronize çalıştırır.
    """

    def __init__(
        self,
        model_path: str = "best.pt",
        center_lat: float = 37.0000,
        center_lon: float = 28.3000,
        base_name: str = "Ana Operasyon Üssü",
        update_hz: float = 4.0
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.base_name = base_name
        self.update_interval = 1.0 / update_hz

        self.environmental_fires: List[Tuple[float, float, float]] = []

        self.geofence_mgr = GeofenceManager()
        self.detector = FireDetector(model_path=model_path)
        self.pso = PSOEngine(geofence_mgr=self.geofence_mgr)

        self.drones: Dict[str, BaseDrone] = {}
        self.latest_annotated_frames: Dict[str, np.ndarray] = {}
        self.latest_detections: Dict[str, List[DetectionResult]] = {}

        self.is_mission_active = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.mission_kind = "fire"
        self.sar_targets = []
        self.perception_epoch = 0
        self._vision_thread = None
        self.loop_error = None
        self.last_control_tick = 0.0
        self.pso.config.dt = self.update_interval
        self.pso.set_aoi(center_lat-.005, center_lat+.005, center_lon-.006, center_lon+.006)

        # Operasyonel istatistikler
        self.mission_start_time = 0.0
        self.mission_elapsed = 0.0
        self.scenario_targets = []
        self.total_fire_detections = 0
        self.leaderboard: List[Dict[str, Any]] = []

    def start(self):
        """Sürü arka plan döngüsünü başlatır."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._swarm_loop, daemon=True)
            self._thread.start()
            self._vision_thread = threading.Thread(target=self._perception_loop, daemon=True)
            self._vision_thread.start()
            print("[SwarmManager] Sürü koordinatörü başlatıldı.")

    def stop(self):
        """Sürü döngüsünü durdurur."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._vision_thread:
            self._vision_thread.join(timeout=2.0)
        print("[SwarmManager] Sürü koordinatörü durduruldu.")

    def register_drone(self, drone: BaseDrone) -> bool:
        """Yeni bir drone'u (Simüle, MAVLink veya Gönüllü) anında sürüye ekler."""
        with self._lock:
            if drone.drone_id in self.drones:
                raise ValueError("Bu drone kimliği zaten kayıtlı")
        if not drone.connect():
            drone.disconnect()
            return False
        with self._lock:
            if drone.drone_id in self.drones:
                drone.disconnect()
                raise ValueError("Bu drone kimliği zaten kayıtlı")
            # Simüle drone ise mevcut çevresel yangın hedeflerini devral
            if isinstance(drone, SimulatedDrone):
                existing_target_coords = {(f[0], f[1]) for f in drone.fire_targets}
                for ef in self.environmental_fires:
                    if (ef[0], ef[1]) not in existing_target_coords:
                        drone.fire_targets.append(ef)

            if isinstance(drone, SimulatedDrone):
                drone.geofence_mgr = self.geofence_mgr
            self.pso.capabilities[drone.drone_id] = drone.capabilities
            self.drones[drone.drone_id] = drone

            # Eğer görev zaten aktifse yeni eklenen drone da derhal kalkış yapsın ve göreve başlasın
            if self.is_mission_active and isinstance(drone, SimulatedDrone):
                if not drone.telemetry.is_in_air:
                    drone.takeoff(target_alt=min(drone.capabilities["search_altitude_m"], drone.capabilities["max_altitude_m"]))
                if drone.mode != DroneMode.TAKEOFF:
                    drone.mode = DroneMode.MISSION_PSO
                    drone.telemetry.mode = drone.mode

            t = drone.get_telemetry()
            self.pso.register_or_update_particle(
                drone_id=drone.drone_id,
                lat=t.lat,
                lon=t.lon,
                alt=t.alt
            )
            print(f"[SwarmManager] Drone sürüye katıldı: {drone.drone_id} (Tip: {drone.drone_type.value})")
            return True

    def remove_drone(self, drone_id: str) -> bool:
        """Drone'u sürüden çıkarır."""
        with self._lock:
            if drone_id in self.drones:
                d = self.drones.pop(drone_id)
                d.disconnect()
                self.pso.remove_particle(drone_id)
                self.latest_annotated_frames.pop(drone_id, None)
                self.latest_detections.pop(drone_id, None)
                for mapping in (self.pso.sectors, self.pso.roles, self.pso.routes, self.pso.route_indices, self.pso.waypoints, self.pso.capabilities):
                    mapping.pop(drone_id, None)
                print(f"[SwarmManager] Drone sürüden ayrıldı: {drone_id}")
                return True
            return False

    def register_volunteer(
        self,
        pilot_name: str,
        lat: float,
        lon: float,
        alt: float = 30.0,
        camera_url: Optional[str] = None
    ) -> VolunteerDrone:
        """Vatandaş / Gönüllü katılımını kolayca kaydeder."""
        vid = f"VOLUNTEER_{uuid.uuid4().hex[:8]}"
        v_drone = VolunteerDrone(
            drone_id=vid,
            pilot_name=pilot_name,
            initial_lat=lat,
            initial_lon=lon,
            initial_alt=alt,
            camera_stream_url=camera_url
        )
        self.register_drone(v_drone)
        return v_drone

    def start_mission(self):
        """Tüm sürü için otonom PSO yangın arama görevini başlatır."""
        with self._lock:
            if not any(hub_controls(d) or (isinstance(d, VolunteerDrone) and time.time()-d.telemetry.last_heartbeat <= 3) for d in self.drones.values()):
                raise ValueError("Göreve katılacak drone yok: simülasyon ekleyin ya da bir MAVLink drone'u "
                                 "uçuş öncesi kontrolden geçirip hub kontrolüne alın")
            if self.is_mission_active:
                return
            self.is_mission_active = True
            self.mission_start_time = time.time()
            for drone in self.drones.values():
                if isinstance(drone, MAVLinkDrone) and hub_controls(drone):
                    self._launch_autopilot(drone)
                    continue
                if not isinstance(drone, SimulatedDrone) or drone.telemetry.battery_percentage <= 20:
                    continue
                if drone.mode in (DroneMode.RTL, DroneMode.LANDING):
                    continue
                if not drone.telemetry.is_in_air:
                    drone.takeoff(target_alt=min(drone.capabilities["search_altitude_m"], drone.capabilities["max_altitude_m"]))
                else:
                    drone.mode = DroneMode.MISSION_PSO
                    drone.telemetry.mode = drone.mode
            print("[SwarmManager] Otonom PSO yangın arama devriyesi başlatıldı!")

    def _launch_autopilot(self, drone: "MAVLinkDrone"):
        """Hub kontrolündeki gerçek otopilotu göreve sokar: havadaysa hemen, yerdeyse kalkışla."""
        if drone.telemetry.is_in_air and drone.flight_mode == "GUIDED":
            drone.control_state = "mission"
            return
        if drone.control_state == "takeoff":
            return
        target = min(drone.capabilities["search_altitude_m"], drone.capabilities["max_altitude_m"])

        def worker():
            if not drone.takeoff(target_alt=target):
                self.loop_error = f"{drone.drone_id}: kalkış yapılamadı - " + "; ".join(drone.status()["messages"][-2:])
                return
            end = time.time() + 90
            while time.time() < end and drone.control_enabled and drone.control_state == "takeoff":
                if drone.telemetry.alt >= target * 0.9:
                    drone.control_state = "mission"
                    return
                time.sleep(0.25)
        threading.Thread(target=worker, daemon=True, name=f"{drone.drone_id}-takeoff").start()

    def pause_mission(self):
        """Görevi duraklatır (drone'lar havada sabit kalır / loiter)."""
        with self._lock:
            if self.is_mission_active:
                self.mission_elapsed += time.time()-self.mission_start_time
            self.is_mission_active = False
            for drone in self.drones.values():
                if isinstance(drone, MAVLinkDrone) and hub_controls(drone):
                    drone.send_velocity(0.0, 0.0, 0.0)
                    continue
                if not isinstance(drone, SimulatedDrone) or drone.mode in (DroneMode.RTL, DroneMode.LANDING):
                    continue
                drone.send_velocity(0.0, 0.0, 0.0)
                drone.mode = DroneMode.ARMED
                drone.telemetry.mode = drone.mode
            print("[SwarmManager] Görev duraklatıldı.")

    def return_to_launch_all(self):
        """Tüm sürüyü emniyetle kalkış noktasına döndürür (RTL)."""
        with self._lock:
            if self.is_mission_active:
                self.mission_elapsed += time.time()-self.mission_start_time
            self.is_mission_active = False
            for drone in self.drones.values():
                if isinstance(drone, SimulatedDrone):
                    drone.return_to_launch()
                elif isinstance(drone, MAVLinkDrone) and (drone.control_enabled or
                                                          drone.control_state in ("takeoff", "mission", "hold")):
                    drone.return_to_launch()
            print("[SwarmManager] Tüm sürüye RTL komutu iletildi.")

    def relocate_swarm(self, new_lat: float, new_lon: float, base_name: Optional[str] = None, regenerate_fires: bool = True):
        """Operasyon merkezini (Üssü) yeni coğrafi koordinata taşır ve sürüyü yeniden konuşlandırır."""
        with self._lock:
            self.is_mission_active = False
            self.mission_elapsed = 0.0
            self.perception_epoch += 1
            self.scenario_targets.clear()
            self.pso.elapsed_seconds = 0.0
            self.latest_annotated_frames.clear()
            self.latest_detections.clear()
            self.pso.particles.clear()
            self.pso.discovered_fire_clusters.clear()
            self.pso._route_key = None
            self.pso.set_aoi(new_lat-.005, new_lat+.005, new_lon-.006, new_lon+.006)
            self.sar_targets.clear()
            self.center_lat = new_lat
            self.center_lon = new_lon
            if base_name:
                self.base_name = base_name
            self.pso.reset_gbest()

            # Yeni üs çevresinde gerçekçi yangın/duman odakları üret (eğer istenmişse)
            if regenerate_fires:
                self.environmental_fires = [
                    (new_lat + 0.0035, new_lon + 0.0040, 0.95),  # ~450m Kuzeydoğu odağı
                    (new_lat - 0.0030, new_lon - 0.0025, 0.88),  # ~380m Güneybatı odağı
                ]
                self.pso.discovered_fire_clusters = []

            # Drone'ları yeni merkezin etrafında daire şeklinde konuşlandır
            idx = 0
            n = len(self.drones)
            for d_id, drone in self.drones.items():
                if not isinstance(drone, SimulatedDrone):
                    continue
                angle = (2.0 * math.pi * idx) / max(1, n)
                r_deg = 0.002  # ~200 metre yarıçap
                d_lat = r_deg * math.cos(angle)
                d_lon = r_deg * math.sin(angle)

                new_pos_lat = new_lat + d_lat
                new_pos_lon = new_lon + d_lon

                if isinstance(drone, SimulatedDrone):
                    drone.home_lat = new_pos_lat
                    drone.home_lon = new_pos_lon
                    drone.telemetry.lat = new_pos_lat
                    drone.telemetry.lon = new_pos_lon
                    drone.telemetry.alt = self.pso.config.search_altitude
                    drone.telemetry.vx = 0.0
                    drone.telemetry.vy = 0.0
                    drone.telemetry.vz = 0.0
                    drone.send_velocity(0, 0, 0)
                    drone.mode = DroneMode.ARMED
                    drone.telemetry.mode = drone.mode
                    if regenerate_fires:
                        drone.fire_targets = list(self.environmental_fires)
                elif isinstance(drone, VolunteerDrone):
                    drone.telemetry.lat = new_pos_lat
                    drone.telemetry.lon = new_pos_lon

                self.pso.register_or_update_particle(
                    drone_id=d_id,
                    lat=new_pos_lat,
                    lon=new_pos_lon,
                    alt=self.pso.config.search_altitude,
                    fitness=0.0
                )
                idx += 1
            print(f"[SwarmManager] Sürü yeni merkeze taşındı: ({new_lat:.5f}, {new_lon:.5f}) - Üs: {self.base_name}")

    def add_manual_fire_spot(self, lat: float, lon: float, intensity: float = 0.95):
        """Saha ihbarı veya kule uyarısı ile yeni bir yangın odağı ekler."""
        with self._lock:
            # Çevresel yangınlar listesine ekle
            self.environmental_fires.append((lat, lon, intensity))

            # Simüle drone'ların algılayabilmesi için listeye ekle
            for drone in self.drones.values():
                if isinstance(drone, SimulatedDrone):
                    drone.fire_targets.append((lat, lon, intensity))

            # Küme olarak kaydet
            self.pso._update_fire_cluster(lat, lon, intensity, source="operator_report")
            print(f"[SwarmManager] Manuel yangın ihbarı eklendi: ({lat:.5f}, {lon:.5f}) - Şiddet: {intensity}")

    def drone_rtl(self, drone_id: str) -> bool:
        """Bireysel drone için acil üsse dönüş (RTL) emri verir."""
        with self._lock:
            if drone_id in self.drones:
                if not isinstance(self.drones[drone_id], (SimulatedDrone, MAVLinkDrone)):
                    raise ValueError("Bu drone'a bağlantı yok (gönüllü köprüsü); dönüşü pilot kendi kumandasından yapar")
                self.drones[drone_id].return_to_launch()
                print(f"[SwarmManager] {drone_id} için bireysel RTL komutu verildi.")
                return True
            return False

    def drone_land(self, drone_id: str) -> bool:
        """Bireysel drone için iniş emri verir."""
        with self._lock:
            if drone_id in self.drones:
                if not isinstance(self.drones[drone_id], (SimulatedDrone, MAVLinkDrone)):
                    raise ValueError("Bu drone'a bağlantı yok (gönüllü köprüsü); inişi pilot kendi kumandasından yapar")
                self.drones[drone_id].land()
                print(f"[SwarmManager] {drone_id} için iniş komutu verildi.")
                return True
            return False

    def drone_takeoff(self, drone_id: str, alt: float = 40.0) -> bool:
        """Bireysel drone için kalkış emri verir."""
        with self._lock:
            if drone_id in self.drones:
                if not hub_controls(self.drones[drone_id]):
                    raise ValueError("Önce uçuş öncesi kontrolden geçirip hub kontrolüne alın")
                self.drones[drone_id].takeoff(target_alt=alt)
                print(f"[SwarmManager] {drone_id} için kalkış komutu verildi.")
                return True
            return False

    def preflight(self, drone_id: str):
        drone = self.drones.get(drone_id)
        if not isinstance(drone, MAVLinkDrone):
            raise ValueError("Uçuş öncesi kontrol yalnızca MAVLink otopilotları içindir")
        checks = drone.preflight()
        if drone.telemetry.lat or drone.telemetry.lon:
            distance = math.hypot((drone.telemetry.lat-self.center_lat)*111139,
                                  (drone.telemetry.lon-self.center_lon)*111139*math.cos(math.radians(self.center_lat)))
            checks.append({"id": "distance", "label": "Üsse en fazla 5 km", "ok": distance <= 5000,
                           "detail": f"{distance:.0f} m"})
        return checks

    def set_drone_control(self, drone_id: str, enable: bool):
        """Operatör onayıyla bir otopilotu hub kontrolüne alır ya da bırakır."""
        drone = self.drones.get(drone_id)
        if not isinstance(drone, MAVLinkDrone):
            raise ValueError("Hub kontrolü yalnızca MAVLink otopilotları içindir")
        if not enable:
            drone.release_control()
            return {"control_enabled": False, "checks": drone.preflight()}
        checks = self.preflight(drone_id)
        failed = [c["label"] for c in checks if not c["ok"]]
        if failed:
            return {"control_enabled": False, "checks": checks, "failed": failed}
        drone.grant_control()
        with self._lock:
            self.pso.capabilities[drone_id] = drone.capabilities
            if self.is_mission_active:
                self._launch_autopilot(drone)
        return {"control_enabled": drone.control_enabled, "checks": checks}

    @synchronized
    def set_wind(self, speed_ms: float, direction_deg: float):
        """Saha rüzgar parametrelerini günceller."""
        self.pso.set_wind(speed_ms, direction_deg)

    @synchronized
    def set_aoi(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float):
        """Arama operasyon sınırlarını (AOI) günceller."""
        self.pso.set_aoi(min_lat, max_lat, min_lon, max_lon)
        self.pso._route_key = None

    @synchronized
    def export_incident_report(self) -> Dict[str, Any]:
        """İtfaiye ve kriz merkezine iletilecek detaylı yangın tespit raporunu üretir."""
        clusters = []
        for c in self.pso.discovered_fire_clusters:
            clusters.append({
                "id": c.get("id"),
                "latitude": round(c.get("lat"), 6),
                "longitude": round(c.get("lon"), 6),
                "google_maps_url": f"https://maps.google.com/?q={c.get('lat')},{c.get('lon')}",
                "confidence_percent": round(c.get("confidence") * 100, 1),
                "detections_count": c.get("detections_count"),
                "status": c.get("status", "candidate"),
                "source": c.get("source"), "kind": c.get("kind")
            })

        return {
            "mission_kind": self.mission_kind,
            "execution_mode": "simulation",
            "report_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "operation_center": {"lat": self.center_lat, "lon": self.center_lon},
            "wind": {"speed_ms": self.pso.wind_speed_ms, "direction_deg": self.pso.wind_direction_deg},
            "active_drones_count": len(self.drones),
            "total_clusters_found": len(clusters),
            "fire_clusters": clusters
        }

    def close_zone(
        self,
        name: str,
        zone_type: ZoneType,
        coordinates: List[Tuple[float, float]],
        min_alt: float = 0.0,
        max_alt: float = 500.0
    ):
        """
        Kullanıcının kapatmak istediği bölgeyi (söndürülen yangın, göl, vs.) Geofence'e ekler.
        Eğer sürünün gbest'i bu kapatılan alanın içine denk geliyorsa gbest derhal sıfırlanır!
        """
        with self._lock:
            zone = self.geofence_mgr.add_zone(
                name=name,
                zone_type=zone_type,
                coordinates=coordinates,
                min_alt=min_alt,
                max_alt=max_alt
            )

            # Sürünün gbest'i bu kapatılan bölgede mi?
            is_inside, _ = self.geofence_mgr.is_point_inside(
                self.pso.gbest_lat, self.pso.gbest_lon, self.pso.gbest_alt
            )
            if is_inside:
                print(f"[SwarmManager] Kapatılan bölge ({name}) mevcut hedefi içeriyor! Hedef sıfırlandı.")
                self.pso.reset_gbest()

            if zone_type != ZoneType.HIGH_RISK_SEARCH:
                self.pso.reset_gbest()
                self.pso.detours.clear()
                for incident in self.pso.discovered_fire_clusters:
                    if zone.polygon.covers(Point(incident['lon'],incident['lat'])):
                        incident['status'] = 'resolved'
                        incident['verified'] = False
            return zone

    @synchronized
    def set_mission_kind(self, kind):
        if kind not in ("fire", "sar"):
            raise ValueError("Görev fire veya sar olmalı")
        if self.is_mission_active:
            raise ValueError("Görev türünü değiştirmeden önce duraklatın")
        self.mission_elapsed = 0.0
        self.mission_kind = self.pso.mission_kind = kind
        self.perception_epoch += 1
        self.pso.reset_gbest()
        self.pso.discovered_fire_clusters.clear()
        self.latest_detections.clear()
        self.latest_annotated_frames.clear()
        for d in self.drones.values():
            d.telemetry.current_fire_score = 0
        for p in self.pso.particles.values():
            p.current_fitness = p.total_detections = 0
        self.total_fire_detections = 0

    @synchronized
    def add_scenario_target(self, lat, lon, confidence=.95, delay_seconds=0):
        target = {"id": f"scenario_{len(self.scenario_targets)+1}", "lat": lat, "lon": lon,
                  "confidence": confidence, "kind": self.mission_kind,
                  "ignition_s": self.pso.elapsed_seconds + delay_seconds, "active": False,
                  "aftershock": delay_seconds > 0, "detected_s": None, "delay_s": None}
        self.scenario_targets.append(target)
        self._ignite_scenario_targets()
        return copy.deepcopy(target)

    def _ignite_scenario_targets(self):
        for target in self.scenario_targets:
            if not target["active"] and target["kind"] == self.mission_kind and target["ignition_s"] <= self.pso.elapsed_seconds:
                target["active"] = True
                self._add_scenario_truth(target["lat"], target["lon"], target["confidence"])

    def _add_scenario_truth(self, lat, lon, confidence):
        targets = self.environmental_fires if self.mission_kind == "fire" else self.sar_targets
        targets.append((lat, lon, confidence))
        for d in self.drones.values():
            if isinstance(d, SimulatedDrone):
                d.fire_targets = list(self.environmental_fires)
        # Hidden scenario truth is never published as an incident.

    DRILL_MATCH_M = 50.0

    def _score_drill(self, lat, lon, drone_id):
        """Tatbikat değerlendirmesi: kamera tahmini yalnızca kendisine EN YAKIN aktif gizli hedefe, o da
        50 m içindeyse sayılır (yan yana iki yangından biri diğerinin tespitiyle "bulunmuş" sayılmaz).
        Yalnızca operatörün sonuç tablosu içindir; planlayıcı gizli hedefleri hiçbir zaman görmez."""
        best = None
        for target in self.scenario_targets:
            if target["active"] and target["kind"] == self.mission_kind:
                d = math.hypot((target["lat"]-lat)*111139, (target["lon"]-lon)*111139*math.cos(math.radians(lat)))
                if best is None or d < best[0]:
                    best = (d, target)
        if best and best[0] <= self.DRILL_MATCH_M and best[1].get("detected_s") is None:
            d, target = best
            target["detected_s"] = round(self.pso.elapsed_seconds, 1)
            target["delay_s"] = round(target["detected_s"] - target["ignition_s"], 1)
            target["detected_by"] = drone_id
            target["error_m"] = round(d, 1)

    @synchronized
    def record_candidate(self, lat, lon, confidence, source="operator_report"):
        return self.pso._update_fire_cluster(lat, lon, confidence, source=source)

    @synchronized
    def update_incident(self, incident_id, status):
        if status not in ("confirmed", "dismissed", "resolved"):
            raise ValueError("Geçersiz olay durumu")
        for c in self.pso.discovered_fire_clusters:
            if c["id"] == incident_id:
                c["status"] = status
                c["status_changed_s"] = self.pso.elapsed_seconds
                c["verified"] = status == "confirmed"
                self.pso.reset_gbest()
                return copy.deepcopy(c)
        raise KeyError(incident_id)

    def _perception_loop(self):
        while self._running:
            self.perceive_once()
            time.sleep(.2)

    def perceive_once(self):
        """A complete observation cycle; inference runs outside the flight-control lock."""
        with self._lock:
            items = list(self.drones.items())
            kind, epoch = self.mission_kind, self.perception_epoch
        for drone_id, drone in items:
            try:
                t = copy.copy(drone.get_telemetry())
                if not t.is_in_air or (not isinstance(drone, SimulatedDrone) and time.time()-t.last_heartbeat > 3):
                    continue
                if isinstance(drone, VolunteerDrone):
                    t, frame = drone.get_camera_observation()
                elif isinstance(drone, (SimulatedDrone, MAVLinkDrone)):
                    frame = drone.get_camera_frame(pose=t)      # kare ve GPS dönüşümü aynı pozdan
                else:
                    frame = drone.get_camera_frame()
                if frame is None:
                    continue
                detections, score, annotated = [], 0.0, frame.copy()
                observed = []
                if kind == "fire":
                    detections, score, annotated = self.detector.detect(frame, t.lat, t.lon, t.alt, t.heading,
                        camera_hfov_deg=drone.capabilities.get("camera_hfov_deg", 84))
                    observed = [(d.estimated_gps[0], d.estimated_gps[1], d.confidence)
                                for d in detections if d.estimated_gps]
                elif isinstance(drone, SimulatedDrone):
                    # Explicit synthetic SAR sensor; no claim that best.pt detects people.
                    annotated = drone.forest_texture.copy()
                    for lat, lon, confidence in list(self.sar_targets):
                        distance = math.hypot((lat-t.lat)*111139, (lon-t.lon)*111139*math.cos(math.radians(t.lat)))
                        if distance < t.alt*.6:
                            observed.append((lat, lon, confidence))
                            score = max(score, confidence)
                import cv2
                label = "SIMULATED CAMERA / " if isinstance(drone, SimulatedDrone) else "CAMERA / "
                if isinstance(drone, MAVLinkDrone) and drone.camera_source is not None:
                    label = "AUTOPILOT + SYNTHETIC DRILL CAMERA / "
                label += "FIRE" if kind == "fire" else "SAR SYNTHETIC SENSOR"
                cv2.rectangle(annotated, (0,440), (640,480), (15,22,29), -1)
                cv2.putText(annotated, label, (10, 465), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
                with self._lock:
                    if epoch != self.perception_epoch or self.drones.get(drone_id) is not drone:
                        continue
                    self.latest_annotated_frames[drone_id] = annotated
                    self.latest_detections[drone_id] = detections
                    suppressed = any((c.get("status") == "confirmed" or
                        (c.get("status") in ("dismissed", "resolved") and self.pso.elapsed_seconds-c.get("status_changed_s", self.pso.elapsed_seconds) < 60)) and
                        math.hypot((c["lat"]-t.lat)*111139, (c["lon"]-t.lon)*111139*math.cos(math.radians(t.lat))) < 100
                        for c in self.pso.discovered_fire_clusters)
                    if suppressed:
                        score = 0.0
                    drone.telemetry.current_fire_score = score
                    p = self.pso.register_or_update_particle(drone_id, t.lat, t.lon, t.alt, score)
                    p.lat, p.lon, p.alt = drone.telemetry.lat, drone.telemetry.lon, drone.telemetry.alt
                    for lat, lon, confidence in observed:
                        if not self.geofence_mgr.is_point_inside(lat, lon, t.alt)[0]:
                            self.record_candidate(lat, lon, confidence, "simulation" if isinstance(drone, SimulatedDrone) else "camera_estimate")
                            self._score_drill(lat, lon, drone_id)
                    drone.telemetry.pbest_score = p.pbest_fitness
                    drone.telemetry.detections_count = p.total_detections
            except Exception as exc:
                self.loop_error = "Algılama: " + str(exc)

    @synchronized
    def tick(self, dt=None):
        dt = self.update_interval if dt is None else min(.5, max(.001, dt))
        self.pso.config.dt = dt
        self._ignite_scenario_targets()
        active = set()
        for drone_id, drone in self.drones.items():
            t = drone.get_telemetry()
            p = self.pso.particles.get(drone_id)
            if p:
                p.lat, p.lon, p.alt = t.lat, t.lon, t.alt
                p.vx, p.vy, p.vz = t.vx, t.vy, t.vz
            if isinstance(drone, SimulatedDrone) and t.is_in_air and drone.mode == DroneMode.MISSION_PSO:
                active.add(drone_id)
            if isinstance(drone, MAVLinkDrone):
                if drone.control_enabled and not drone.link_ok():
                    # Bağlantı koptu: hub susar, otopilotun kendi failsafe'i (GCS kaybı -> RTL) devrededir
                    drone.control_enabled = False
                    drone.control_state = "lost"
                elif hub_controls(drone) and t.is_in_air and drone.control_state == "mission":
                    active.add(drone_id)
            if isinstance(drone, VolunteerDrone):
                if time.time()-t.last_heartbeat <= 3 and t.battery_percentage > 20 and t.alt > 1:
                    active.add(drone_id)
                else:
                    drone.send_velocity(0, 0, 0)
            if drone_id in active and drone_id not in self.pso.particles:
                self.pso.register_or_update_particle(drone_id, t.lat, t.lon, t.alt)
        if self.is_mission_active:
            for drone_id, (vx, vy, vz, target_alt) in self.pso.step(active).items():
                self.drones[drone_id].send_velocity(vx, vy, vz)
                if isinstance(self.drones[drone_id], VolunteerDrone):
                    self.drones[drone_id].assigned_target_alt = target_alt
        for drone in self.drones.values():
            if isinstance(drone, SimulatedDrone):
                drone.aoi_bounds = self.pso.aoi_bounds
                drone.update_physics(dt)
        self._update_leaderboard()
        self.last_control_tick = time.time()

    def _swarm_loop(self):
        previous = time.monotonic()
        while self._running:
            started = time.monotonic()
            try:
                self.tick(started-previous)
            except Exception as exc:
                self.loop_error = str(exc)
                self.pause_mission()
            previous = started
            time.sleep(max(.01, self.update_interval-(time.monotonic()-started)))

    def _update_leaderboard(self):
        """En çok yangın bulan ve en yüksek skoru üreten drone'ların listesi."""
        board = []
        for p in self.pso.particles.values():
            d = self.drones.get(p.drone_id)
            d_type = d.drone_type.value if d else "UNKNOWN"
            board.append({
                "drone_id": p.drone_id,
                "type": d_type,
                "total_detections": p.total_detections,
                "pbest_score": round(p.pbest_fitness, 3),
                "current_score": round(p.current_fitness, 3),
                "altitude": round(p.alt, 1),
                "battery": round(d.telemetry.battery_percentage, 1) if d else 100.0
            })

        # Tespit sayısı ve skora göre sırala
        board.sort(key=lambda x: (x["total_detections"], x["pbest_score"]), reverse=True)
        self.leaderboard = board

    @synchronized
    def get_swarm_state(self) -> Dict[str, Any]:
        """Web arayüzüne gönderilecek tam telemetri ve harita durumu paketi."""
        drones_telemetry = {}
        for d_id, d in self.drones.items():
            t = d.get_telemetry()
            p = self.pso.particles.get(d_id)
            drones_telemetry[d_id] = {
                "drone_id": d_id,
                "type": d.drone_type.value,
                "mode": d.mode.value,
                "lat": t.lat,
                "lon": t.lon,
                "alt": round(t.alt, 1),
                "speed": round(t.speed, 1),
                "heading": round(t.heading, 1),
                "battery": round(t.battery_percentage, 1),
                "is_low_battery": getattr(t, "is_low_battery", False),
                "current_score": round(t.current_fire_score, 2),
                "pbest_score": round(p.pbest_fitness, 2) if p else 0.0,
                "pbest_pos": [p.pbest_lat, p.pbest_lon] if p else [t.lat, t.lon],
                "detections_count": t.detections_count,
                "is_armed": t.is_armed,
                "is_in_air": t.is_in_air,
                "role": (self.pso.roles.get(d_id, "standby") if self.is_mission_active and d.mode == DroneMode.MISSION_PSO else "standby") if hub_controls(d) else ("pilot_advisory" if isinstance(d, VolunteerDrone) else "observer"),
                "waypoint": self.pso.waypoints.get(d_id),
                "telemetry_age_s": round(max(0, time.time()-t.last_heartbeat), 1) if t.last_heartbeat else None,
                "safety_hold": getattr(d, "safety_hold", False),
                "control_enabled": hub_controls(d),
                "autopilot": d.status() if isinstance(d, MAVLinkDrone) else None,
                "preflight": self.preflight(d_id) if isinstance(d, MAVLinkDrone) and not d.control_enabled else None,
                "capabilities": dict(d.capabilities),
                "sector": self.pso.sectors.get(d_id)
            }

        autopilots = [d for d in self.drones.values() if isinstance(d, MAVLinkDrone) and d.control_enabled]
        return {
            "mission_kind": self.mission_kind,
            "execution_mode": "autopilot" if autopilots else "simulation",
            "search_strategy": self.pso.config.search_strategy,
            "coverage": self.pso.coverage_snapshot(),
            "readiness": {"physical_flight_enabled": bool(autopilots), "fire_model_loaded": self.detector.model is not None,
                          "sar_person_model_loaded": False, "control_error": self.loop_error},
            "is_mission_active": self.is_mission_active,
            "mission_elapsed_seconds": int(self.mission_elapsed + (time.time()-self.mission_start_time if self.is_mission_active else 0)),
            "base_station": {"name": self.base_name, "lat": self.center_lat, "lon": self.center_lon},
            "operation_center": {"lat": self.center_lat, "lon": self.center_lon},
            "wind": {"speed_ms": self.pso.wind_speed_ms, "direction_deg": self.pso.wind_direction_deg},
            "aoi_bounds": self.pso.aoi_bounds,
            "drones_count": len(self.drones),
            "gbest": {
                "lat": self.pso.gbest_lat,
                "lon": self.pso.gbest_lon,
                "alt": self.pso.gbest_alt,
                "fitness": round(self.pso.gbest_fitness, 3),
                "found_by": self.pso.gbest_drone_id
            },
            "fire_clusters": copy.deepcopy(self.pso.discovered_fire_clusters),
            "geofence_zones": self.geofence_mgr.to_geojson(),
            "drones": drones_telemetry,
            "leaderboard": self.leaderboard
        }

    def get_annotated_frame_jpeg(self, drone_id: str) -> Optional[bytes]:
        """Web UI video feed'i için JPEG formatında kare döndürür."""
        import cv2
        frame = self.latest_annotated_frames.get(drone_id)
        if frame is None and drone_id in self.drones:
            frame = self.drones[drone_id].get_camera_frame()

        if frame is not None:
            ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                return buf.tobytes()
        return None
