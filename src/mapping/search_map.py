"""
PyreSwarm - Arama Haritası ve Kapsama Katmanı (Search Map & Cell Coverage)
Arama alanını ayrık (discretized) metrik ızgara hücrelerine (grid cells - örn. 50m x 50m) böler.
Kamera izdüşümünden (FOV footprint) kapsama oranını (coverage %), gereksiz örtüşmeyi (redundancy)
ve taranmamış alanları hesaplar.
[THEORETICAL_BOUND / SIMULATED]
"""

import math
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from shapely.geometry import Point, Polygon


@dataclass
class GridCell:
    cell_id: Tuple[int, int]
    center_lat: float
    center_lon: float
    searched_count: int = 0
    last_visit_time: float = 0.0
    fire_evidence: float = 0.0
    smoke_evidence: float = 0.0
    is_excluded: bool = False

    @property
    def is_searched(self) -> bool:
        return self.searched_count > 0


class SearchMap:
    """
    Arama alanının hücre bazlı durumunu, ısı haritasını ve kapsama analizini yöneten harita motoru.
    """

    def __init__(
        self,
        cell_size_meters: float = 50.0,
        meters_per_degree: float = 111139.0
    ):
        self.cell_size_m = cell_size_meters
        self.meters_per_degree = meters_per_degree

        self.boundary_polygon: Optional[Polygon] = None
        self.cells: Dict[Tuple[int, int], GridCell] = {}
        self.origin_lat: float = 0.0
        self.origin_lon: float = 0.0

    def init_grid_from_boundary(self, boundary_coords: List[Tuple[float, float]]):
        """Arama poligonuna göre ızgara hücrelerini oluşturur."""
        if len(boundary_coords) < 3:
            return

        self.boundary_polygon = Polygon([(p[1], p[0]) for p in boundary_coords])  # lon, lat
        self.cells.clear()

        lats = [p[0] for p in boundary_coords]
        lons = [p[1] for p in boundary_coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        self.origin_lat = min_lat
        self.origin_lon = min_lon

        cos_lat = math.cos(math.radians(min_lat))
        deg_lat = self.cell_size_m / self.meters_per_degree
        deg_lon = self.cell_size_m / (self.meters_per_degree * cos_lat)

        n_lat = int(math.ceil((max_lat - min_lat) / deg_lat)) + 1
        n_lon = int(math.ceil((max_lon - min_lon) / deg_lon)) + 1

        for i in range(n_lat):
            for j in range(n_lon):
                c_lat = min_lat + (i + 0.5) * deg_lat
                c_lon = min_lon + (j + 0.5) * deg_lon
                pt = Point(c_lon, c_lat)

                if self.boundary_polygon.contains(pt):
                    cell = GridCell(
                        cell_id=(i, j),
                        center_lat=round(c_lat, 6),
                        center_lon=round(c_lon, 6)
                    )
                    self.cells[(i, j)] = cell

    def update_drone_footprint(
        self,
        drone_lat: float,
        drone_lon: float,
        drone_alt: float,
        camera_hfov_deg: float = 84.0,
        camera_vfov_deg: float = 56.0
    ) -> int:
        """
        Kamera görüş alanı yer izdüşümünü hesaplayarak içindeki hücreleri 'taranmış' olarak işaretler.
        Döndürür: Bu adımda taranan hücre sayısı
        """
        if not self.cells:
            return 0

        # Zemin görüş genişliği ve boyu (metre)
        w_ground_m = 2.0 * drone_alt * math.tan(math.radians(camera_hfov_deg / 2.0))
        l_ground_m = 2.0 * drone_alt * math.tan(math.radians(camera_vfov_deg / 2.0))
        radius_m = max(w_ground_m, l_ground_m) / 2.0

        now = time.time()
        updated_count = 0
        cos_lat = math.cos(math.radians(drone_lat))
        m_lon = self.meters_per_degree * cos_lat

        for cell in self.cells.values():
            if cell.is_excluded:
                continue

            dx = (cell.center_lon - drone_lon) * m_lon
            dy = (cell.center_lat - drone_lat) * self.meters_per_degree

            if abs(dx) <= (w_ground_m / 2.0) and abs(dy) <= (l_ground_m / 2.0):
                cell.searched_count += 1
                cell.last_visit_time = now
                updated_count += 1

        return updated_count

    def apply_exclusion_zone(self, nfz_coords: List[Tuple[float, float]]):
        """Belirtilen poligon içindeki hücreleri 'excluded' yapar (aramadan çıkarır)."""
        if len(nfz_coords) < 3:
            return
        poly = Polygon([(p[1], p[0]) for p in nfz_coords])
        for cell in self.cells.values():
            if poly.contains(Point(cell.center_lon, cell.center_lat)):
                cell.is_excluded = True

    def get_coverage_metrics(self) -> Dict[str, float]:
        """
        Toplam kapsama oranı (%), gereksiz mükerrer örtüşme oranı ve alan ölçümlerini döndürür.
        """
        valid_cells = [c for c in self.cells.values() if not c.is_excluded]
        total_valid = len(valid_cells)
        if total_valid == 0:
            return {
                "coverage_percent": 0.0,
                "redundant_ratio": 0.0,
                "total_area_km2": 0.0,
                "searched_area_km2": 0.0
            }

        searched_cells = [c for c in valid_cells if c.is_searched]
        num_searched = len(searched_cells)
        coverage_pct = (num_searched / float(total_valid)) * 100.0

        total_visits = sum(c.searched_count for c in searched_cells)
        # Mükerrer tarama: 1'den fazla ziyaret edilenlerin toplam ziyarete oranı
        redundant_visits = sum(max(0, c.searched_count - 1) for c in searched_cells)
        redundant_ratio = (redundant_visits / float(total_visits)) if total_visits > 0 else 0.0

        cell_area_km2 = (self.cell_size_m * self.cell_size_m) / 1_000_000.0
        total_area_km2 = round(total_valid * cell_area_km2, 3)
        searched_area_km2 = round(num_searched * cell_area_km2, 3)

        return {
            "coverage_percent": round(coverage_pct, 2),
            "redundant_ratio": round(redundant_ratio, 3),
            "total_area_km2": total_area_km2,
            "searched_area_km2": searched_area_km2
        }

    def get_unexplored_coordinates(self) -> List[Tuple[float, float]]:
        """Henüz taranmamış geçerli hücre merkez koordinatlarını döndürür."""
        return [
            (c.center_lat, c.center_lon)
            for c in self.cells.values()
            if not c.is_excluded and not c.is_searched
        ]

    def to_geojson_cells(self) -> List[Dict[str, Any]]:
        """Web haritasında görselleştirmek üzere hücreleri listeler."""
        result = []
        for c in self.cells.values():
            result.append({
                "lat": c.center_lat,
                "lon": c.center_lon,
                "count": c.searched_count,
                "excluded": c.is_excluded
            })
        return result
