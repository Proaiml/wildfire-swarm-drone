"""
PyreSwarm - Sürü Çeşitliliği ve Çoklu Çekici Arşivi (Swarm Diversity & Multi-Attractor)
Sürü Çöküşünü (Swarm Collapse) önler: Bir yangın bulunduğunda tüm sürünün tek noktaya yığılmasını
engeller. Onaylanan yangına en fazla K=2 drone tahsis eder; kalan drone'lar için bu bölgeyi
tabu (exclusion) yaparak diğer yangınları aramalarını zorunlu kılar.
"""

from typing import List, Dict, Tuple, Set, Optional
import math
from src.drones.state import DroneState, DroneMode
from src.incidents.incident_manager import FireIncident, IncidentStatus


class SwarmDiversityManager:
    """
    Sürü çeşitliliğini ölçen, çoklu çekici (multi-attractor) arşivini yöneten ve
    sürü çöküşünü önleyen orkestratör.
    """

    def __init__(
        self,
        max_drones_per_incident: int = 2,
        taboo_radius_meters: float = 150.0,
        min_diversity_threshold_m: float = 60.0,
        meters_per_degree: float = 111139.0
    ):
        self.max_drones_per_incident = max_drones_per_incident
        self.taboo_radius_m = taboo_radius_meters
        self.min_diversity_m = min_diversity_threshold_m
        self.meters_per_degree = meters_per_degree

        # Incident -> List[assigned_drone_id]
        self._incident_assignments: Dict[str, List[str]] = {}

    def calculate_swarm_diversity(self, drones: List[DroneState]) -> float:
        """
        Sürünün uzamsal dağılımını (çeşitlilik metriği - metre) hesaplar.
        D(t) = (1/N) * sum( || p_i - p_mean || )
        [THEORETICAL_BOUND / SIMULATED]
        """
        active_drones = [d for d in drones if d.is_in_air]
        if len(active_drones) <= 1:
            return 100.0  # Tek drone için çöküş söz konusu değildir

        # Ortalama ağırlık merkezi (lat, lon)
        mean_lat = sum(d.lat for d in active_drones) / len(active_drones)
        mean_lon = sum(d.lon for d in active_drones) / len(active_drones)
        cos_mean = math.cos(math.radians(mean_lat))

        total_distance = 0.0
        for d in active_drones:
            dx = (d.lon - mean_lon) * self.meters_per_degree * cos_mean
            dy = (d.lat - mean_lat) * self.meters_per_degree
            dist = math.hypot(dx, dy)
            total_distance += dist

        diversity = total_distance / len(active_drones)
        return round(diversity, 2)

    def is_swarm_collapsed(self, drones: List[DroneState]) -> bool:
        """Sürü çeşitliliği asgari eşiğin altına indiyse True döner."""
        return self.calculate_swarm_diversity(drones) < self.min_diversity_m

    def update_incident_allocations(
        self,
        incidents: List[FireIncident],
        drones: List[DroneState]
    ) -> Dict[str, str]:
        """
        Her doğrulanmış veya şüpheli yangına en fazla max_drones_per_incident kadar drone atar.
        Döndürür: drone_id -> assigned_incident_id (veya None)
        """
        # Aktif incident'ları filtrele
        targetable_incidents = [
            inc for inc in incidents
            if inc.status in (IncidentStatus.CONFIRMED, IncidentStatus.SUSPECTED, IncidentStatus.MONITORING)
        ]

        assignments: Dict[str, str] = {}
        assigned_drones: Set[str] = set()

        for inc in targetable_incidents:
            # Bu olaya en yakın ve uygun drone'ları sırala
            candidates = []
            for d in drones:
                if d.drone_id in assigned_drones:
                    continue
                if not d.is_in_air or d.is_critical_battery:
                    continue

                dx = (d.lon - inc.centroid_lon) * self.meters_per_degree * math.cos(math.radians(inc.centroid_lat))
                dy = (d.lat - inc.centroid_lat) * self.meters_per_degree
                dist = math.hypot(dx, dy)
                candidates.append((dist, d.drone_id))

            candidates.sort(key=lambda x: x[0])
            selected = candidates[:self.max_drones_per_incident]

            self._incident_assignments[inc.incident_id] = [cid for _, cid in selected]
            for _, cid in selected:
                assignments[cid] = inc.incident_id
                assigned_drones.add(cid)

        return assignments

    def is_point_in_taboo_zone(
        self,
        lat: float,
        lon: float,
        drone_id: str,
        incidents: List[FireIncident]
    ) -> bool:
        """
        Eğer bir drone belirli bir yangına atanmamışsa, o yangının çevresi (taboo zone)
        o drone için taranması gereksiz yasaklı/doymuş bölgedir.
        """
        for inc in incidents:
            if inc.status not in (IncidentStatus.CONFIRMED, IncidentStatus.MONITORING):
                continue

            # Bu drone bu yangına tahsis edilmiş mi?
            assigned_list = self._incident_assignments.get(inc.incident_id, [])
            if drone_id in assigned_list:
                continue  # Bu drone atanmış, yangına yaklaşabilir

            # Atanmamış drone için tabu kontrolü
            dx = (lon - inc.centroid_lon) * self.meters_per_degree * math.cos(math.radians(inc.centroid_lat))
            dy = (lat - inc.centroid_lat) * self.meters_per_degree
            dist = math.hypot(dx, dy)

            if dist <= self.taboo_radius_m:
                return True

        return False
