"""
PyreSwarm - Deterministik Çoklu Drone ve Yangın Simülatörü (Swarm Simulator)
Tekrarlanabilir deneyler için tohum (random seed) destekli, sentetik yangın modelleri,
sensör fizibilitesi ve hata enjeksiyonu (fault injection) içeren simülasyon ortamı.
[SIMULATED]
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any

from src.drones.state import DroneState, DroneMode, DroneType, DroneHealth
from src.drones.adapter import SimulationDroneAdapter
from src.safety.safety_plane import SafetyFlightPlane
from src.safety.collision import CollisionAvoidance
from src.safety.battery_failsafe import BatteryEnergyModel
from src.swarm.diversity import SwarmDiversityManager
from src.swarm.optimizer import SwarmOptimizer
from src.mapping.search_map import SearchMap
from src.perception.fusion import SpatialTemporalEvidenceFusion, DroneObservation
from src.incidents.incident_manager import FireIncidentManager, IncidentStatus


@dataclass
class SyntheticFire:
    fire_id: str
    lat: float
    lon: float
    radius_m: float = 25.0
    intensity: float = 0.90
    smoke_radius_m: float = 80.0
    is_detected: bool = False
    first_detected_at_step: Optional[int] = None
    confirmed_at_step: Optional[int] = None


@dataclass
class SimulationMetrics:
    total_steps: int = 0
    simulated_time_sec: float = 0.0
    ttfd_sec: Optional[float] = None          # Time to First Detection
    ttc_sec: Optional[float] = None           # Time to Confirmation
    final_coverage_pct: float = 0.0
    redundant_coverage_ratio: float = 0.0
    total_distance_km: float = 0.0
    total_energy_kj: float = 0.0
    incidents_confirmed: int = 0
    total_fires_simulated: int = 0


class SwarmSimulationEngine:
    """
    Tüm simülasyon bileşenlerini koordine eden ve ölçülebilir metrikler üreten ana motor.
    """

    def __init__(
        self,
        center_lat: float = 37.0,
        center_lon: float = 28.0,
        area_km2: float = 4.0,
        num_drones: int = 5,
        num_fires: int = 2,
        random_seed: int = 42,
        meters_per_degree: float = 111139.0
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.area_km2 = area_km2
        self.num_drones = num_drones
        self.num_fires = num_fires
        self.seed = random_seed
        self.meters_per_degree = meters_per_degree

        # Deterministik tohum ayarı
        random.seed(self.seed)

        # 1. Arama Alanı ve Güvenlik Düzlemi
        side_m = math.sqrt(area_km2 * 1_000_000.0)
        half_m = side_m / 2.0
        cos_c = math.cos(math.radians(center_lat))

        d_lat = half_m / self.meters_per_degree
        d_lon = half_m / (self.meters_per_degree * cos_c)

        self.boundary = [
            (center_lat - d_lat, center_lon - d_lon),
            (center_lat - d_lat, center_lon + d_lon),
            (center_lat + d_lat, center_lon + d_lon),
            (center_lat + d_lat, center_lon - d_lon)
        ]

        self.safety_plane = SafetyFlightPlane()
        self.safety_plane.set_search_boundary(self.boundary)

        self.collision_avoidance = CollisionAvoidance(safe_distance_m=25.0)
        self.battery_model = BatteryEnergyModel()
        self.diversity_manager = SwarmDiversityManager(taboo_radius_meters=120.0)
        self.optimizer = SwarmOptimizer(
            safety_plane=self.safety_plane,
            collision_avoidance=self.collision_avoidance,
            diversity_manager=self.diversity_manager
        )

        self.search_map = SearchMap(cell_size_meters=50.0)
        self.search_map.init_grid_from_boundary(self.boundary)

        self.fusion = SpatialTemporalEvidenceFusion()
        self.incident_manager = FireIncidentManager()

        # 2. Sentetik Yangınlar
        self.fires: List[SyntheticFire] = []
        for i in range(num_fires):
            f_lat = center_lat + (random.random() - 0.5) * (d_lat * 1.6)
            f_lon = center_lon + (random.random() - 0.5) * (d_lon * 1.6)
            self.fires.append(SyntheticFire(
                fire_id=f"FIRE_{i+1:02d}",
                lat=round(f_lat, 6),
                lon=round(f_lon, 6)
            ))

        # 3. Drone Filosu ve Adaptörler
        self.drones: List[DroneState] = []
        self.adapters: List[SimulationDroneAdapter] = []

        for i in range(num_drones):
            d_id = f"DRONE_{i+1:02d}"
            # Üs konumu
            start_lat = center_lat - d_lat * 0.85
            start_lon = center_lon + (i - (num_drones - 1) / 2.0) * (20.0 / (self.meters_per_degree * cos_c))

            state = DroneState(
                drone_id=d_id,
                drone_type=DroneType.SIMULATED,
                lat=start_lat,
                lon=start_lon,
                alt=0.0,
                home_lat=start_lat,
                home_lon=start_lon,
                home_alt=0.0
            )
            adapter = SimulationDroneAdapter(state)
            adapter.connect()
            adapter.takeoff(target_altitude_m=65.0)

            self.drones.append(state)
            self.adapters.append(adapter)

        # Metrikler
        self.current_step = 0
        self.total_distance_travelled_m = 0.0
        self.metrics = SimulationMetrics(total_fires_simulated=num_fires)

    def step(self, dt: float = 1.0, use_pso: bool = True):
        """Tek bir simülasyon saniyesini işletir."""
        self.current_step += 1
        self.optimizer.update_iteration()
        all_incidents = self.incident_manager.get_all_incidents()

        # Yangın tahsislerini güncelle
        self.diversity_manager.update_incident_allocations(all_incidents, self.drones)

        # Drone adım optimizasyonu ve hareketi
        for i, (state, adapter) in enumerate(zip(self.drones, self.adapters)):
            if not state.is_in_air:
                continue

            old_lat, old_lon = state.lat, state.lon

            # 1. Batarya ve RTL Denetimi
            self.battery_model.update_drone_battery_simulation(state, dt_seconds=dt, is_moving=state.speed > 0.5)
            must_rtl, _, _ = self.battery_model.evaluate_rth_requirement(state)
            if must_rtl and state.mode != DroneMode.RETURNING:
                adapter.return_to_home()

            # 2. PSO Hedef Belirleme
            if use_pso and state.mode == DroneMode.SEARCHING:
                target_lat, target_lon, target_alt = self.optimizer.step_drone(
                    drone=state,
                    all_drones=self.drones,
                    incidents=all_incidents,
                    dt=dt
                )
                adapter.goto(target_lat, target_lon, target_alt)

            # 3. Fizik İlerlemesi
            adapter.step_simulation(dt=dt)

            # Kat edilen mesafe
            cos_l = math.cos(math.radians(state.lat))
            d_x = (state.lon - old_lon) * self.meters_per_degree * cos_l
            d_y = (state.lat - old_lat) * self.meters_per_degree
            self.total_distance_travelled_m += math.hypot(d_x, d_y)

            # 4. Kapsama Alanı Güncellemesi
            self.search_map.update_drone_footprint(
                drone_lat=state.lat,
                drone_lon=state.lon,
                drone_alt=state.alt
            )

            # 5. Yangın Algılama Simülasyonu
            self._simulate_drone_perception(state)

    def _simulate_drone_perception(self, drone: DroneState):
        """Drone kamerasının yangınları görüp görmediğini modeller."""
        # Görüş yarıçapı ~ İrtifa * tan(HFOV/2)
        fov_radius_m = drone.alt * math.tan(math.radians(42.0))
        cos_d = math.cos(math.radians(drone.lat))

        for fire in self.fires:
            dx = (fire.lon - drone.lon) * self.meters_per_degree * cos_d
            dy = (fire.lat - drone.lat) * self.meters_per_degree
            dist = math.hypot(dx, dy)

            # Görüş alanı içinde mi?
            if dist <= fov_radius_m:
                # Tespit simülasyonu (Merkeze yakınlaştıkça güven artar)
                rel_dist = dist / max(1.0, fov_radius_m)
                conf = max(0.40, fire.intensity * (1.0 - 0.4 * rel_dist))

                # Gözlem nesnesi
                obs = DroneObservation(
                    drone_id=drone.drone_id,
                    timestamp=time.time(),
                    drone_lat=drone.lat,
                    drone_lon=drone.lon,
                    drone_alt=drone.alt,
                    estimated_fire_lat=fire.lat + (random.random() - 0.5) * 0.0001,
                    estimated_fire_lon=fire.lon + (random.random() - 0.5) * 0.0001,
                    confidence=round(conf, 3),
                    class_name="fire",
                    box_area_ratio=0.10
                )

                fused = self.fusion.add_observation(obs)
                if fused:
                    inc = self.incident_manager.process_evidence(fused)

                    # İlk Tespit Zamanı (TTFD)
                    if not fire.is_detected:
                        fire.is_detected = True
                        fire.first_detected_at_step = self.current_step
                        if self.metrics.ttfd_sec is None:
                            self.metrics.ttfd_sec = float(self.current_step)

                    # Doğrulama Zamanı (TTC)
                    if inc.status in (IncidentStatus.CONFIRMED, IncidentStatus.SUSPECTED):
                        if fire.confirmed_at_step is None:
                            fire.confirmed_at_step = self.current_step
                            if self.metrics.ttc_sec is None and inc.status == IncidentStatus.CONFIRMED:
                                self.metrics.ttc_sec = float(self.current_step)

                    # PSO global best ve pbest güncellemesi
                    drone.pbest_score = fused.fused_confidence
                    drone.pbest_lat = fused.centroid_lat
                    drone.pbest_lon = fused.centroid_lon
                    drone.pbest_alt = drone.alt
                    self.optimizer.update_global_best(
                        pbest_lat=fused.centroid_lat,
                        pbest_lon=fused.centroid_lon,
                        pbest_alt=drone.alt,
                        score=fused.fused_confidence
                    )

    def inject_fault(self, drone_id: str, fault_type: str):
        """Simülasyon sırasında kontrollü arıza enjeksiyonu yapar."""
        for d in self.drones:
            if d.drone_id == drone_id:
                if fault_type == "GPS_LOSS":
                    d.health = DroneHealth.GPS_LOSS
                    d.gps_fix = False
                elif fault_type == "COMM_LOSS":
                    d.health = DroneHealth.COMM_LOSS
                    d.network_quality = 0
                elif fault_type == "CRITICAL_BATTERY":
                    d.battery_percentage = 10.0
                    d.is_critical_battery = True
                    d.health = DroneHealth.CRITICAL_BATTERY
                elif fault_type == "CAMERA_FAILURE":
                    d.health = DroneHealth.CAMERA_FAILURE
                return True
        return False

    def run_simulation(self, max_steps: int = 300) -> SimulationMetrics:
        """Belirtilen adım kadar simülasyonu işletir ve nihai metrikleri çıkarır."""
        for _ in range(max_steps):
            self.step(dt=1.0)

            # Tüm yangınlar doğrulandıysa ve kapsama %90'ı geçtiyse erken bitirilebilir
            confirmed_cnt = len(self.incident_manager.get_confirmed_incidents())
            if confirmed_cnt >= self.num_fires and self.metrics.ttc_sec is not None:
                break

        # Nihai Metrikler
        cov = self.search_map.get_coverage_metrics()
        self.metrics.total_steps = self.current_step
        self.metrics.simulated_time_sec = float(self.current_step)
        self.metrics.final_coverage_pct = cov["coverage_percent"]
        self.metrics.redundant_coverage_ratio = cov["redundant_ratio"]
        self.metrics.total_distance_km = round(self.total_distance_travelled_m / 1000.0, 3)
        self.metrics.incidents_confirmed = len(self.incident_manager.get_confirmed_incidents())

        # Toplam tüketilen enerji (tahmini 180W * t * N / 1000 = kJ)
        self.metrics.total_energy_kj = round((180.0 * self.current_step * len(self.drones)) / 1000.0, 1)

        return self.metrics
