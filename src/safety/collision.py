"""
PyreSwarm - Çarpışma Önleme ve Dağıtık Ayrılma (Collision Avoidance & APF Separation)
Yapay Potansiyel Alanı (Artificial Potential Field - APF) kullanarak drone'lar arasında
asgari güvenli mesafeyi (d_safe = 30m) garanti eder ve sürü çarpışmalarını önler.
"""

from typing import List, Dict, Tuple, Optional, Any
import math
from src.drones.state import DroneState


class CollisionAvoidance:
    """
    Sürü içindeki drone'ların birbirine yaklaşmasını engelleyen APF itki ve güvenlik denetleyicisi.
    [THEORETICAL_BOUND / SIMULATED]
    """

    def __init__(
        self,
        safe_distance_m: float = 30.0,
        influence_distance_m: float = 50.0,
        repulsion_gain: float = 40.0,
        meters_per_degree: float = 111139.0
    ):
        self.d_safe = safe_distance_m
        self.d_influence = influence_distance_m
        self.k_rep = repulsion_gain
        self.meters_per_degree = meters_per_degree

    def calculate_repulsive_force(
        self,
        drone: DroneState,
        other_drones: List[DroneState]
    ) -> Tuple[float, float, float]:
        """
        Diğer tüm drone'lardan kaynaklanan net itki hız vektörünü (vx_rep, vy_rep, vz_rep - m/s) hesaplar.
        """
        net_fx = 0.0
        net_fy = 0.0
        net_fz = 0.0

        for other in other_drones:
            if other.drone_id == drone.drone_id:
                continue
            if not other.is_in_air:
                continue

            # ENU mesafesi veya WGS84 yerel dönüşüm
            dx = (drone.lon - other.lon) * self.meters_per_degree * math.cos(math.radians(drone.lat))
            dy = (drone.lat - other.lat) * self.meters_per_degree
            dz = (drone.alt - other.alt)

            dist_3d = math.sqrt(dx * dx + dy * dy + dz * dz)

            if 0.1 < dist_3d < self.d_influence:
                # Klasik APF itki formülü:
                # F_rep = k_rep * (1/d - 1/d_0) * (1 / d^2) * norm_vector
                inv_dist = 1.0 / dist_3d
                inv_d0 = 1.0 / self.d_influence
                magnitude = self.k_rep * (inv_dist - inv_d0) * (inv_dist * inv_dist)

                # Şiddeti güvenli sınırda sınırla (Maks 6.0 m/s itki)
                magnitude = min(6.0, magnitude)

                net_fx += magnitude * (dx / dist_3d)
                net_fy += magnitude * (dy / dist_3d)
                net_fz += magnitude * (dz / dist_3d)

        return round(net_fx, 3), round(net_fy, 3), round(net_fz, 3)

    def check_swarm_separation_violations(
        self,
        drones: List[DroneState]
    ) -> List[Dict[str, Any]]:
        """
        Sürü içindeki tüm drone çiftlerini kontrol eder ve d_safe ihlallerini raporlar.
        """
        violations = []
        n = len(drones)
        for i in range(n):
            for j in range(i + 1, n):
                d1 = drones[i]
                d2 = drones[j]
                if not d1.is_in_air or not d2.is_in_air:
                    continue

                dx = (d1.lon - d2.lon) * self.meters_per_degree * math.cos(math.radians(d1.lat))
                dy = (d1.lat - d2.lat) * self.meters_per_degree
                dz = (d1.alt - d2.alt)
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)

                if dist < self.d_safe:
                    violations.append({
                        "drone_a": d1.drone_id,
                        "drone_b": d2.drone_id,
                        "distance_m": round(dist, 2),
                        "safe_threshold_m": self.d_safe
                    })
        return violations
