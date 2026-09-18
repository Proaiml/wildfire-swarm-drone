"""
PyreSwarm - 3D Parçacık Sürü Optimizasyonu (3D-PSO Swarm Optimizer)
Fiziksel drone kısıtlarına uyarlanmış, adaptif atalet (w), bilişsel (c1) ve sosyal (c2)
ağırlıklara sahip, Güvenlik Düzlemi ve APF çarpışma önleme ile kenetlenmiş sürü arama motoru.
"""

import math
import random
from typing import List, Dict, Optional, Tuple
from src.drones.state import DroneState, DroneMode
from src.safety.safety_plane import SafetyFlightPlane
from src.safety.collision import CollisionAvoidance
from src.swarm.goal_attainment import GoalAttainmentFitness
from src.swarm.diversity import SwarmDiversityManager
from src.incidents.incident_manager import FireIncident


class SwarmOptimizer:
    """
    Sürü arama hedeflerini (waypoint) üreten ve koordine eden ana 3D-PSO optimizasyon motoru.
    [THEORETICAL_BOUND / SIMULATED]
    """

    def __init__(
        self,
        safety_plane: SafetyFlightPlane,
        collision_avoidance: CollisionAvoidance,
        diversity_manager: SwarmDiversityManager,
        fitness_evaluator: Optional[GoalAttainmentFitness] = None,
        w_max: float = 0.85,
        w_min: float = 0.40,
        c1_initial: float = 2.0,
        c2_initial: float = 1.2,
        max_iterations: int = 200,
        meters_per_degree: float = 111139.0
    ):
        self.safety = safety_plane
        self.collision = collision_avoidance
        self.diversity = diversity_manager
        self.fitness = fitness_evaluator or GoalAttainmentFitness()

        self.w_max = w_max
        self.w_min = w_min
        self.c1_init = c1_initial
        self.c2_init = c2_initial
        self.max_iter = max_iterations
        self.meters_per_degree = meters_per_degree

        self.current_iteration = 0
        self.global_best_lat: Optional[float] = None
        self.global_best_lon: Optional[float] = None
        self.global_best_alt: float = 65.0
        self.global_best_score: float = -float("inf")

    def update_iteration(self):
        """Her döngü adımında adaptif parametreleri güncellemek için sayaç."""
        self.current_iteration = min(self.max_iter, self.current_iteration + 1)

    def get_adaptive_inertia(self) -> float:
        """Lineer azalan atalet katsayısı w(t)."""
        ratio = self.current_iteration / float(max(1, self.max_iter))
        return self.w_max - (self.w_max - self.w_min) * ratio

    def get_adaptive_coefficients(self) -> Tuple[float, float]:
        """Başlangıçta keşif (c1 yüksek), ilerleyen zamanda işbirliği (c2 yüksek)."""
        ratio = self.current_iteration / float(max(1, self.max_iter))
        c1 = self.c1_init - 0.8 * ratio
        c2 = self.c2_init + 0.8 * ratio
        return round(c1, 3), round(c2, 3)

    def update_global_best(self, pbest_lat: float, pbest_lon: float, pbest_alt: float, score: float):
        """Sürü genelindeki en iyi konumu günceller."""
        if score > self.global_best_score:
            self.global_best_score = score
            self.global_best_lat = pbest_lat
            self.global_best_lon = pbest_lon
            self.global_best_alt = pbest_alt

    def step_drone(
        self,
        drone: DroneState,
        all_drones: List[DroneState],
        incidents: List[FireIncident],
        dt: float = 1.0
    ) -> Tuple[float, float, float]:
        """
        Tekil bir drone için bir sonraki güvenli hedef koordinatlarını (lat, lon, alt) hesaplar.
        """
        # Eğer drone havada değilse veya acil durumda ise konum değiştirme
        if not drone.is_in_air or drone.mode in (DroneMode.RETURNING, DroneMode.LANDING, DroneMode.EMERGENCY):
            return drone.lat, drone.lon, drone.alt

        w = self.get_adaptive_inertia()
        c1, c2 = self.get_adaptive_coefficients()

        # Eğer sürü çöküşü (collapse) yaşanıyorsa bilişsel (keşif) bileşeni artır
        if self.diversity.is_swarm_collapsed(all_drones):
            c1 *= 1.5

        r1 = random.random()
        r2 = random.random()

        # Metrik uzayda farklar (Doğu, Kuzey, Yukarı - metre)
        cos_lat = math.cos(math.radians(drone.lat))
        m_lon = self.meters_per_degree * cos_lat

        # Kişisel En İyiye (pbest) çekim
        dx_pbest = (drone.pbest_lon - drone.lon) * m_lon if drone.pbest_score > 0 else 0.0
        dy_pbest = (drone.pbest_lat - drone.lat) * self.meters_per_degree if drone.pbest_score > 0 else 0.0
        dz_pbest = (drone.pbest_alt - drone.alt)

        # Küresel En İyiye (gbest) çekim (Tabu kontrolü uygulanır)
        dx_gbest, dy_gbest, dz_gbest = 0.0, 0.0, 0.0
        if self.global_best_lat is not None and self.global_best_score > 0:
            is_taboo = self.diversity.is_point_in_taboo_zone(
                self.global_best_lat, self.global_best_lon, drone.drone_id, incidents
            )
            if not is_taboo:
                dx_gbest = (self.global_best_lon - drone.lon) * m_lon
                dy_gbest = (self.global_best_lat - drone.lat) * self.meters_per_degree
                dz_gbest = (self.global_best_alt - drone.alt)

        # PSO Hız Güncellemesi: v(t+1) = w*v(t) + c1*r1*(pbest - x) + c2*r2*(gbest - x)
        vx_new = w * drone.vx + c1 * r1 * (dx_pbest * 0.1) + c2 * r2 * (dx_gbest * 0.1)
        vy_new = w * drone.vy + c1 * r1 * (dy_pbest * 0.1) + c2 * r2 * (dy_gbest * 0.1)
        vz_new = w * drone.vz + c1 * r1 * (dz_pbest * 0.05) + c2 * r2 * (dz_gbest * 0.05)

        # Eğer henüz yangın sinyali yoksa: Sektörel Keşif ve Alan Dağılımı (Sector Dispersion)
        if self.global_best_score <= 0.05:
            if self.safety.search_polygon is not None and not self.safety.search_polygon.is_empty:
                min_lon, min_lat, max_lon, max_lat = self.safety.search_polygon.bounds
                n_drones = max(1, len(all_drones))
                try:
                    d_idx = [d.drone_id for d in all_drones].index(drone.drone_id)
                except ValueError:
                    d_idx = 0

                # Drone'a tahsis edilen sektör enlemi
                sec_lat = min_lat + (d_idx + 0.5) * ((max_lat - min_lat) / float(n_drones))
                # Doğu-Batı salınım fazı
                phase = (self.current_iteration * 0.03 + d_idx * (math.pi / float(n_drones))) % (2.0 * math.pi)
                sec_lon = min_lon + 0.5 * (max_lon - min_lon) * (1.0 + math.sin(phase))

                dx_sec = (sec_lon - drone.lon) * m_lon
                dy_sec = (sec_lat - drone.lat) * self.meters_per_degree
                dist_sec = math.hypot(dx_sec, dy_sec)

                if dist_sec > 2.0:
                    vx_new = 12.0 * (dx_sec / dist_sec)
                    vy_new = 12.0 * (dy_sec / dist_sec)
                else:
                    vx_new = 0.0
                    vy_new = 0.0
            else:
                # Poligon yoksa pusula yönünü koru
                curr_speed = math.hypot(vx_new, vy_new)
                if curr_speed < 1.0:
                    rad = math.radians(drone.heading) if drone.heading > 0 else random.uniform(0, 2 * math.pi)
                    vx_new = 12.0 * math.cos(rad)
                    vy_new = 12.0 * math.sin(rad)
                else:
                    scale = 11.5 / curr_speed
                    vx_new = (vx_new * scale)
                    vy_new = (vy_new * scale)

        # Çarpışma Önleme (APF) İtki Kuvvetlerini Ekle
        fx_rep, fy_rep, fz_rep = self.collision.calculate_repulsive_force(drone, all_drones)
        vx_new += fx_rep
        vy_new += fy_rep
        vz_new += fz_rep

        # Güvenlik Düzlemi Hız Sınırlaması (Clamping)
        vx_clamped, vy_clamped, vz_clamped = self.safety.clamp_velocity(vx_new, vy_new, vz_new)
        drone.vx = vx_clamped
        drone.vy = vy_clamped
        drone.vz = vz_clamped
        drone.speed = round(math.hypot(vx_clamped, vy_clamped), 2)

        # Aday Yeni Konum
        delta_east_m = vx_clamped * dt
        delta_north_m = vy_clamped * dt
        candidate_lat = drone.lat + (delta_north_m / self.meters_per_degree)
        candidate_lon = drone.lon + (delta_east_m / m_lon)
        candidate_alt = drone.alt + vz_clamped * dt

        # Güvenlik Düzlemi Projeksiyonu (NFZ ve Poligon Sınırları)
        safe_lat, safe_lon, safe_alt, was_modified = self.safety.validate_and_project_waypoint(
            current_lat=drone.lat, current_lon=drone.lon, current_alt=drone.alt,
            target_lat=candidate_lat, target_lon=candidate_lon, target_alt=candidate_alt
        )

        if was_modified:
            # Poligon sınırına veya engele çarpıldığında vektörü içeriye yansıt (boundary reflection)
            drone.vx = -drone.vx * 0.85 + (random.random() - 0.5) * 3.0
            drone.vy = -drone.vy * 0.85 + (random.random() - 0.5) * 3.0

        drone.assigned_target_lat = safe_lat
        drone.assigned_target_lon = safe_lon
        drone.assigned_target_alt = safe_alt

        return safe_lat, safe_lon, safe_alt
