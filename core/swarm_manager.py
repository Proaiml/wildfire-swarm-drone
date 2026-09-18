"""
PyreSwarm - Sürü Yönetim ve Koordinasyon Merkezi (Swarm Manager)
Tüm drone'ların, PSO motorunun, YOLO tespit katmanının ve coğrafi kısıtların entegre yönetimi.
"""

import time
import math
import threading
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

from core.geofence_manager import GeofenceManager, ZoneType
from core.fire_detector import FireDetector, DetectionResult
from core.pso_engine import PSOEngine, PSOConfig
from hardware.drone_base import BaseDrone, DroneMode, DroneType, DroneTelemetry
from hardware.simulated_drone import SimulatedDrone
from hardware.mavlink_drone import MAVLinkDrone
from hardware.volunteer_bridge import VolunteerDrone


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
        update_hz: float = 4.0
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.update_interval = 1.0 / update_hz

        self.geofence_mgr = GeofenceManager()
        self.detector = FireDetector(model_path=model_path)
        self.pso = PSOEngine(geofence_mgr=self.geofence_mgr)

        self.drones: Dict[str, BaseDrone] = {}
        self.latest_annotated_frames: Dict[str, np.ndarray] = {}
        self.latest_detections: Dict[str, List[DetectionResult]] = {}

        self.is_mission_active = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Operasyonel istatistikler
        self.mission_start_time = 0.0
        self.total_fire_detections = 0
        self.leaderboard: List[Dict[str, Any]] = []

    def start(self):
        """Sürü arka plan döngüsünü başlatır."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._swarm_loop, daemon=True)
            self._thread.start()
            print("[SwarmManager] Sürü koordinatörü başlatıldı.")

    def stop(self):
        """Sürü döngüsünü durdurur."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[SwarmManager] Sürü koordinatörü durduruldu.")

    def register_drone(self, drone: BaseDrone) -> bool:
        """Yeni bir drone'u (Simüle, MAVLink veya Gönüllü) anında sürüye ekler."""
        with self._lock:
            self.drones[drone.drone_id] = drone
            drone.connect()
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
        vid = f"VOLUNTEER_{int(time.time()) % 10000:04d}"
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
            self.is_mission_active = True
            self.mission_start_time = time.time()
            for drone in self.drones.values():
                if not drone.telemetry.is_in_air:
                    drone.takeoff(target_alt=self.pso.config.search_altitude)
                else:
                    drone.mode = DroneMode.MISSION_PSO
                    drone.telemetry.mode = drone.mode
            print("[SwarmManager] Otonom PSO yangın arama devriyesi başlatıldı!")

    def pause_mission(self):
        """Görevi duraklatır (drone'lar havada sabit kalır / loiter)."""
        with self._lock:
            self.is_mission_active = False
            for drone in self.drones.values():
                drone.send_velocity(0.0, 0.0, 0.0)
                drone.mode = DroneMode.ARMED
                drone.telemetry.mode = drone.mode
            print("[SwarmManager] Görev duraklatıldı.")

    def return_to_launch_all(self):
        """Tüm sürüyü emniyetle kalkış noktasına döndürür (RTL)."""
        with self._lock:
            self.is_mission_active = False
            for drone in self.drones.values():
                drone.return_to_launch()
            print("[SwarmManager] Tüm sürüye RTL komutu iletildi.")

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

            return zone

    def _swarm_loop(self):
        """Ana koordinasyon döngüsü (Vision + Telemetry + PSO Stepping)."""
        while self._running:
            loop_start = time.time()

            try:
                # 1. Her drone için kamera ve telemetri güncellemesi
                with self._lock:
                    drone_items = list(self.drones.items())

                for drone_id, drone in drone_items:
                    # Fizik simülasyonu güncellemesi (Simüle drone ise)
                    if isinstance(drone, SimulatedDrone):
                        drone.update_physics(dt=self.update_interval)

                    t = drone.get_telemetry()

                    # Kamera karesi çekimi ve YOLO inferansı
                    frame = drone.get_camera_frame()
                    if frame is not None:
                        detections, score, annotated = self.detector.detect(
                            frame=frame,
                            drone_lat=t.lat,
                            drone_lon=t.lon,
                            drone_alt=t.alt,
                            drone_yaw_deg=t.heading
                        )
                        self.latest_annotated_frames[drone_id] = annotated
                        self.latest_detections[drone_id] = detections

                        # Drone telemetrisine tespit skoru yansıt
                        t.current_fire_score = score
                        if score > 0.3:
                            self.total_fire_detections += len(detections)

                        # PSO Parçacık durumunu güncelle
                        self.pso.register_or_update_particle(
                            drone_id=drone_id,
                            lat=t.lat,
                            lon=t.lon,
                            alt=t.alt,
                            fitness=score
                        )
                        t.pbest_score = self.pso.particles[drone_id].pbest_fitness
                        t.detections_count = self.pso.particles[drone_id].total_detections

                # 2. Eğer görev aktifse PSO Adımını çalıştır ve hız komutlarını ilet
                if self.is_mission_active:
                    commands = self.pso.step()
                    for drone_id, (vx, vy, vz, target_alt) in commands.items():
                        if drone_id in self.drones:
                            d = self.drones[drone_id]
                            if d.telemetry.is_in_air and d.mode == DroneMode.MISSION_PSO:
                                d.send_velocity(vx, vy, vz)

                # 3. Liderlik Tablosunu Güncelle
                self._update_leaderboard()

            except Exception as e:
                print(f"[SwarmManager] Döngü hatası: {e}")

            elapsed = time.time() - loop_start
            sleep_time = max(0.01, self.update_interval - elapsed)
            time.sleep(sleep_time)

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
                "current_score": round(t.current_fire_score, 2),
                "pbest_score": round(p.pbest_fitness, 2) if p else 0.0,
                "pbest_pos": [p.pbest_lat, p.pbest_lon] if p else [t.lat, t.lon],
                "detections_count": t.detections_count,
                "is_armed": t.is_armed,
                "is_in_air": t.is_in_air
            }

        return {
            "is_mission_active": self.is_mission_active,
            "mission_elapsed_seconds": int(time.time() - self.mission_start_time) if self.is_mission_active else 0,
            "drones_count": len(self.drones),
            "gbest": {
                "lat": self.pso.gbest_lat,
                "lon": self.pso.gbest_lon,
                "alt": self.pso.gbest_alt,
                "fitness": round(self.pso.gbest_fitness, 3),
                "found_by": self.pso.gbest_drone_id
            },
            "fire_clusters": self.pso.discovered_fire_clusters,
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
