"""
PyreSwarm - Coğrafi Sınır ve Yasaklı Bölge Yöneticisi (Geofence Manager)
Kullanıcı tarafından kapatılan yangın alanları, göller ve uçuşa yasak bölgeleri yönetir.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any
import math
import uuid
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import nearest_points


class ZoneType(str, Enum):
    FIRE_EXTINGUISHED = "fire_extinguished"   # Taranmış / Söndürülmüş yangın odağı (Tekrar bakmaya gerek yok)
    WATER_BODY = "water_body"                 # Göl / Nehir / Deniz (Yangın çıkmayacak alan)
    NO_FLY_ZONE = "no_fly_zone"               # Uçuşa yasak / Tehlikeli bölge (Kesinlikle girilemez)
    HIGH_RISK_SEARCH = "high_risk_search"     # Özel öncelikli arama bölgesi (Pozitif çekim alanı)


@dataclass
class GeofenceZone:
    id: str
    name: str
    zone_type: ZoneType
    coordinates: List[Tuple[float, float]]    # [(lat, lon), ...]
    min_alt: float = 0.0                      # Minimum irtifa (metre)
    max_alt: float = 500.0                    # Maksimum irtifa (metre)
    safety_margin_meters: float = 25.0        # Güvenli tampon bölge mesafesi
    created_at: float = field(default_factory=lambda: 0.0)
    polygon: Optional[Polygon] = field(default=None, repr=False)

    def __post_init__(self):
        if not self.polygon and len(self.coordinates) >= 3:
            # Shapely (x=lon, y=lat) formatında çalışır
            shapely_coords = [(lon, lat) for lat, lon in self.coordinates]
            self.polygon = Polygon(shapely_coords)


class GeofenceManager:
    """
    Sürü için coğrafi kısıtları, kapatılan bölgeleri ve itici potansiyel alanları yönetir.
    """

    # 1 Enlem derecesi ~ 111,139 metre, 1 Boylam derecesi ~ 111,139 * cos(lat) metre
    METERS_PER_DEGREE = 111139.0

    def __init__(self):
        self.zones: Dict[str, GeofenceZone] = {}

    def add_zone(
        self,
        name: str,
        zone_type: ZoneType,
        coordinates: List[Tuple[float, float]],
        min_alt: float = 0.0,
        max_alt: float = 500.0,
        safety_margin_meters: float = 25.0,
        zone_id: Optional[str] = None
    ) -> GeofenceZone:
        """Yeni bir kapatılmış alan veya kısıtlı bölge ekler."""
        if len(coordinates) < 3:
            raise ValueError("Bir poligon oluşturmak için en az 3 koordinat noktası gereklidir.")

        zid = zone_id or str(uuid.uuid4())[:8]
        zone = GeofenceZone(
            id=zid,
            name=name,
            zone_type=zone_type,
            coordinates=coordinates,
            min_alt=min_alt,
            max_alt=max_alt,
            safety_margin_meters=safety_margin_meters
        )
        self.zones[zid] = zone
        return zone

    def remove_zone(self, zone_id: str) -> bool:
        """Kapatılmış alanı kaldırır."""
        if zone_id in self.zones:
            del self.zones[zone_id]
            return True
        return False

    def get_zone(self, zone_id: str) -> Optional[GeofenceZone]:
        return self.zones.get(zone_id)

    def get_all_zones(self) -> List[GeofenceZone]:
        return list(self.zones.values())

    def clear(self):
        self.zones.clear()

    def is_point_inside(self, lat: float, lon: float, alt: float = 50.0) -> Tuple[bool, Optional[GeofenceZone]]:
        """
        Noktanın herhangi bir kısıtlı/kapatılmış alanın içinde olup olmadığını kontrol eder.
        """
        p = Point(lon, lat)
        for zone in self.zones.values():
            if zone.min_alt <= alt <= zone.max_alt and zone.polygon and zone.polygon.contains(p):
                return True, zone
        return False, None

    def calculate_repulsion_vector(
        self,
        lat: float,
        lon: float,
        alt: float = 50.0,
        max_repulsion_velocity: float = 5.0
    ) -> Tuple[float, float]:
        """
        Yasaklı/kapatılmış alanlara yaklaşan veya giren drone için itici hız vektörü (dlat, dlon) üretir.
        Yapay Potansiyel Alanlar (Artificial Potential Fields) mantığıyla çalışır.
        """
        total_dlat = 0.0
        total_dlon = 0.0
        p = Point(lon, lat)

        cos_lat = math.cos(math.radians(lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        for zone in self.zones.values():
            if not zone.polygon:
                continue
            if not (zone.min_alt <= alt <= zone.max_alt):
                continue
            if zone.zone_type == ZoneType.HIGH_RISK_SEARCH:
                continue  # Bu itici değil çekici alandır

            # Mesafeyi derece cinsinden metreye dönüştürerek hesaplayalım
            # Shapely üzerinde nokta ile poligon sınırının en yakın noktası
            nearest_p, _ = nearest_points(zone.polygon.exterior, p)
            dx_m = (p.x - nearest_p.x) * m_per_deg_lon
            dy_m = (p.y - nearest_p.y) * self.METERS_PER_DEGREE
            dist_m = math.hypot(dx_m, dy_m)

            is_inside = zone.polygon.contains(p)

            # Eğer poligon içindeyse veya güvenlik sınırının içindeyse itki uygula
            if is_inside or dist_m < zone.safety_margin_meters:
                if is_inside:
                    # İçindeyse en yakın dış sınıra doğru çok güçlü itki
                    strength = max_repulsion_velocity * 1.5
                    # Yön: en yakın sınır noktasına doğru (dışarıya çıkmak için)
                    angle = math.atan2(p.y - nearest_p.y, p.x - nearest_p.x)
                    if dist_m < 1e-6:
                        # Tam merkezdeyse rastgele veya kuzeye doğru it
                        angle = math.pi / 2
                else:
                    # Dışındaysa mesafeye ters orantılı itki
                    factor = (zone.safety_margin_meters - dist_m) / zone.safety_margin_meters
                    strength = max_repulsion_velocity * (factor ** 2)
                    angle = math.atan2(dy_m, dx_m)

                # Metre/sn hız bileşenleri
                vx = strength * math.cos(angle)
                vy = strength * math.sin(angle)

                # Derece/sn cinsine çevir
                total_dlon += vx / m_per_deg_lon
                total_dlat += vy / self.METERS_PER_DEGREE

        return total_dlat, total_dlon

    def get_fitness_penalty(self, lat: float, lon: float, alt: float = 50.0) -> float:
        """
        PSO fitness hesaplamasında, kapatılmış veya yasaklı alanların içindeki
        veya yakınındaki noktalara ceza puanı uygular (0.0 - 1.0 arasında ceza çarpanı).
        """
        p = Point(lon, lat)
        cos_lat = math.cos(math.radians(lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        penalty = 0.0

        for zone in self.zones.values():
            if not zone.polygon:
                continue

            if zone.zone_type == ZoneType.HIGH_RISK_SEARCH:
                # Çekici alan, ceza yok, hatta teşvik edilebilir
                continue

            if zone.polygon.contains(p):
                # Alanın tam içindeyse çok ağır ceza (drone buralara odaklanmamalı)
                if zone.zone_type == ZoneType.NO_FLY_ZONE:
                    return 1000.0  # Uçuşa yasak alan: sonsuz ceza
                elif zone.zone_type == ZoneType.FIRE_EXTINGUISHED:
                    return 500.0   # Söndürülmüş alan: tekrar gitme
                elif zone.zone_type == ZoneType.WATER_BODY:
                    return 300.0   # Göl: yangın olamaz

            # Kenara yakınsa kademeli ceza
            nearest_p, _ = nearest_points(zone.polygon.exterior, p)
            dx_m = (p.x - nearest_p.x) * m_per_deg_lon
            dy_m = (p.y - nearest_p.y) * self.METERS_PER_DEGREE
            dist_m = math.hypot(dx_m, dy_m)

            if dist_m < zone.safety_margin_meters:
                decay = (zone.safety_margin_meters - dist_m) / zone.safety_margin_meters
                penalty += 100.0 * decay

        return penalty

    def to_geojson(self) -> Dict[str, Any]:
        """Web haritasında Leaflet GeoJSON layer olarak gösterilmek üzere GeoJSON üretir."""
        features = []
        for zone in self.zones.values():
            # GeoJSON koordinatları [lon, lat] biçimindedir
            coords = [[lon, lat] for lat, lon in zone.coordinates]
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])  # Poligonu kapat

            color_map = {
                ZoneType.FIRE_EXTINGUISHED: "#ff8800",
                ZoneType.WATER_BODY: "#0088ff",
                ZoneType.NO_FLY_ZONE: "#ff0033",
                ZoneType.HIGH_RISK_SEARCH: "#00ff66",
            }

            features.append({
                "type": "Feature",
                "id": zone.id,
                "properties": {
                    "id": zone.id,
                    "name": zone.name,
                    "zone_type": zone.zone_type.value,
                    "color": color_map.get(zone.zone_type, "#ffffff"),
                    "safety_margin": zone.safety_margin_meters,
                    "min_alt": zone.min_alt,
                    "max_alt": zone.max_alt,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }
