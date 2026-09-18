"""
PyreSwarm - Güvenlik ve Uçuş Düzlemi (Safety Flight Plane)
Zorunlu kısıt projeksiyonu: Hiçbir yapay zeka veya PSO algoritması güvenlik kurallarını bypass edemez.
Uçuş irtifa sınırları, hız limitleri, arama poligonu ve Uçuşa Yasak Bölge (NFZ) kontrollerini garanti eder.
"""

from typing import List, Tuple, Optional, Dict, Any
import math
from shapely.geometry import Point, Polygon, LineString


class SafetyFlightPlane:
    """
    Tüm üretilen hedef waypoint'lerini ve yörüngeleri denetleyen,
    gerekirse kırpan (clamping) veya güvenli alana projeksiyonunu yapan sert güvenlik katmanı.
    """

    def __init__(
        self,
        min_altitude_m: float = 25.0,
        max_altitude_m: float = 120.0,
        max_speed_ms: float = 14.0,
        safe_margin_meters: float = 15.0,
        meters_per_degree: float = 111139.0
    ):
        self.min_alt = min_altitude_m
        self.max_alt = max_altitude_m
        self.max_speed = max_speed_ms
        self.safe_margin_m = safe_margin_meters
        self.meters_per_degree = meters_per_degree

        self.search_polygon: Optional[Polygon] = None
        self.no_fly_polygons: List[Polygon] = []

    def set_search_boundary(self, boundary_coords: List[Tuple[float, float]]):
        """Arama operasyon alanının dış poligonunu tanımlar (lat, lon)."""
        if len(boundary_coords) >= 3:
            # Shapely (x=lon, y=lat) formatında çalışır
            self.search_polygon = Polygon([(p[1], p[0]) for p in boundary_coords])

    def add_no_fly_zone(self, nfz_coords: List[Tuple[float, float]]):
        """Uçuşa yasak / arama dışı poligon ekler (lat, lon)."""
        if len(nfz_coords) >= 3:
            self.no_fly_polygons.append(Polygon([(p[1], p[0]) for p in nfz_coords]))

    def clear_no_fly_zones(self):
        self.no_fly_polygons.clear()

    def validate_and_project_waypoint(
        self,
        current_lat: float,
        current_lon: float,
        current_alt: float,
        target_lat: float,
        target_lon: float,
        target_alt: float
    ) -> Tuple[float, float, float, bool]:
        """
        Önerilen hedef noktasını denetler. Güvenlik sınırlarını aşarsa güvenli noktaya projekte eder.
        Döndürür: (safe_lat, safe_lon, safe_alt, was_modified)
        """
        was_modified = False

        # 1. İrtifa Sınırları (Altitude Clamping)
        safe_alt = target_alt
        if safe_alt < self.min_alt:
            safe_alt = self.min_alt
            was_modified = True
        elif safe_alt > self.max_alt:
            safe_alt = self.max_alt
            was_modified = True

        target_pt = Point(target_lon, target_lat)
        safe_lon = target_lon
        safe_lat = target_lat

        # 2. Arama Poligonu Dışına Çıkma Kontrolü
        if self.search_polygon is not None and not self.search_polygon.is_empty:
            if not self.search_polygon.contains(target_pt):
                # Poligonun en yakın sınır noktasına çek
                nearest_pt = self.search_polygon.boundary.interpolate(
                    self.search_polygon.boundary.project(target_pt)
                )
                safe_lon = float(nearest_pt.x)
                safe_lat = float(nearest_pt.y)
                was_modified = True
                target_pt = Point(safe_lon, safe_lat)

        # 3. Uçuşa Yasak Bölge (NFZ) İhlali Kontrolü
        for nfz in self.no_fly_polygons:
            if nfz.contains(target_pt):
                # Yasak alanın dışına doğru safe_margin kadar it
                boundary_pt = nfz.boundary.interpolate(nfz.boundary.project(target_pt))
                # Mevcut konumdan hedef yönüne doğru geri çekilme
                dx = safe_lon - current_lon
                dy = safe_lat - current_lat
                norm = math.hypot(dx, dy)
                if norm > 1e-7:
                    # Geri çekme vektörü
                    margin_deg = (self.safe_margin_m / self.meters_per_degree)
                    safe_lon = float(boundary_pt.x) - (dx / norm) * margin_deg
                    safe_lat = float(boundary_pt.y) - (dy / norm) * margin_deg
                else:
                    safe_lon = float(boundary_pt.x)
                    safe_lat = float(boundary_pt.y)

                was_modified = True
                target_pt = Point(safe_lon, safe_lat)

        # 4. Yörünge Hat Kesişim Kontrolü (Uçuş hattı NFZ'yi deliyor mu?)
        current_pt = Point(current_lon, current_lat)
        trajectory_line = LineString([current_pt, target_pt])
        for nfz in self.no_fly_polygons:
            if trajectory_line.intersects(nfz):
                # Doğrudan hat kesişiyorsa, drone mevcut konumunun biraz ilerisinde durmalı
                intersection = trajectory_line.intersection(nfz.boundary)
                if not intersection.is_empty:
                    # Kesişim noktasına gelmeden durdur
                    safe_lon = current_lon * 0.8 + safe_lon * 0.2
                    safe_lat = current_lat * 0.8 + safe_lat * 0.2
                    was_modified = True
                    break

        return round(safe_lat, 6), round(safe_lon, 6), round(safe_alt, 2), was_modified

    def clamp_velocity(self, vx: float, vy: float, vz: float) -> Tuple[float, float, float]:
        """Hız vektörünün büyüklüğünü max_speed sınırında tutar."""
        speed_horiz = math.hypot(vx, vy)
        scale = 1.0
        if speed_horiz > self.max_speed:
            scale = self.max_speed / speed_horiz

        clamped_vx = vx * scale
        clamped_vy = vy * scale
        # Dikey hız sınırı: Maksimum 4.0 m/s tırmanış/alçalış
        clamped_vz = max(-4.0, min(4.0, vz))

        return round(clamped_vx, 3), round(clamped_vy, 3), round(clamped_vz, 3)
