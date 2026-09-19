"""
PyreSwarm - 3D Uyarlanabilir Parçacık Sürü Optimizasyon Motoru (PSO Engine)
Yangın tespitinde fiziksel kısıtlar, dinamik irtifa/hız optimizasyonu,
çarpışma önleme (APF) ve kapatılmış alan kaçınması içeren modifiye PSO.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import math
import random
import time
import numpy as np

from core.geofence_manager import GeofenceManager
from core.routing import plan_detour


@dataclass
class SwarmParticleState:
    drone_id: str
    lat: float
    lon: float
    alt: float                          # İrtifa (metre)
    vx: float = 0.0                     # Hız doğu (m/s)
    vy: float = 0.0                     # Hız kuzey (m/s)
    vz: float = 0.0                     # Dikey hız (m/s)
    heading: float = 0.0                # Yönelim açısı (derece)
    current_fitness: float = 0.0        # Anlık yangın skoru

    # Kişisel En İyi (Personal Best - pbest)
    pbest_lat: float = 0.0
    pbest_lon: float = 0.0
    pbest_alt: float = 50.0
    pbest_fitness: float = -1.0
    pbest_timestamp: float = 0.0

    # Dinamik uçuş optimizasyon parametreleri
    target_speed: float = 8.0           # m/s
    optimal_altitude: float = 70.0      # m (Arama vs Detay dengesi)
    total_detections: int = 0           # Bu drone'un toplam yangın tespit sayısı

    def __post_init__(self):
        if self.pbest_fitness < 0:
            self.pbest_lat = self.lat
            self.pbest_lon = self.lon
            self.pbest_alt = self.alt
            self.pbest_fitness = self.current_fitness


@dataclass
class PSOConfig:
    # PSO Temel Parametreleri
    inertia_weight: float = 0.65         # Atalet katsayısı (w)
    cognitive_coeff: float = 1.35        # Bireysel öğrenme katsayısı (c1 - pbest çekimi)
    social_coeff: float = 1.65           # Sosyal öğrenme katsayısı (c2 - gbest çekimi)
    exploration_factor: float = 0.25     # Rastgele keşif rüzgarı

    # Hız ve İrtifa Kısıtları
    min_speed: float = 2.0               # Minimum seyir hızı (m/s)
    max_speed: float = 14.0              # Maksimum güvenli hız (m/s)
    min_altitude: float = 25.0           # Minimum uçuş irtifası (metre - ağaç/engel emniyeti)
    max_altitude: float = 120.0          # Maksimum yasal/operasyonel irtifa (metre)
    search_altitude: float = 85.0        # Yangın aranırken tercih edilen geniş açı irtifası
    inspect_altitude: float = 35.0       # Yangın teyit edilirken inilecek detay irtifası

    # Güvenlik ve Ayrılma (Collision Avoidance)
    safe_drone_distance_m: float = 30.0  # Sürü içi minimum ayrılma mesafesi
    repulsion_gain: float = 4.0          # Drone'ların birbirini itme kuvveti çarpanı
    geofence_repulsion_gain: float = 6.0 # Yasaklı bölgeden kaçış itme kuvveti

    # Zaman adımı
    dt: float = 0.5                      # Güncelleme zaman aralığı (saniye)


class PSOEngine:
    """
    Sürü Drone Yangın Arama ve Çevreleme için 3D PSO Motoru.
    """

    METERS_PER_DEGREE = 111139.0

    def __init__(
        self,
        config: Optional[PSOConfig] = None,
        geofence_mgr: Optional[GeofenceManager] = None
    ):
        self.config = config or PSOConfig()
        self.geofence_mgr = geofence_mgr or GeofenceManager()
        self.particles: Dict[str, SwarmParticleState] = {}

        # Küresel En İyi (Global Best - gbest)
        self.gbest_lat: float = 0.0
        self.gbest_lon: float = 0.0
        self.gbest_alt: float = self.config.search_altitude
        self.gbest_fitness: float = 0.0
        self.gbest_drone_id: Optional[str] = None
        self.gbest_timestamp: float = 0.0

        # Çoklu Yangın Odakları (Multi-Modal / Clusters)
        self.discovered_fire_clusters: List[Dict[str, Any]] = []

        # Saha Rüzgar Modeli (Duman Sürüklenmesi)
        self.wind_speed_ms: float = 3.0       # m/s
        self.wind_direction_deg: float = 45.0 # 0=Kuzey, 90=Doğu, 45=Poyraz

        # Operasyon Arama Sınırları (AOI - Area of Interest)
        self.aoi_bounds: Optional[Dict[str, float]] = None
        self.capabilities = {}
        self.sectors = {}
        self.detours = {}
        self.routes = {}
        self.route_indices = {}
        self.roles = {}
        self.waypoints = {}
        self._route_key = None
        self.mission_kind = "fire"
        self.elapsed_seconds = 0.0

    def set_wind(self, speed_ms: float, direction_deg: float):
        """Saha rüzgar parametrelerini günceller."""
        self.wind_speed_ms = max(0.0, min(30.0, speed_ms))
        self.wind_direction_deg = direction_deg % 360.0

    def set_aoi(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float):
        """Operasyon arama sınırını (AOI) belirler."""
        self.aoi_bounds = {
            "min_lat": min(min_lat, max_lat),
            "max_lat": max(min_lat, max_lat),
            "min_lon": min(min_lon, max_lon),
            "max_lon": max(min_lon, max_lon)
        }

    def register_or_update_particle(
        self,
        drone_id: str,
        lat: float,
        lon: float,
        alt: float,
        fitness: float = 0.0
    ) -> SwarmParticleState:
        """Yeni bir drone parçacığını sisteme kaydeder veya mevcut olanı günceller."""
        if drone_id not in self.particles:
            particle = SwarmParticleState(
                drone_id=drone_id,
                lat=lat,
                lon=lon,
                alt=alt,
                current_fitness=fitness,
                pbest_lat=lat,
                pbest_lon=lon,
                pbest_alt=alt,
                pbest_fitness=fitness
            )
            self.particles[drone_id] = particle
        else:
            particle = self.particles[drone_id]
            particle.lat = lat
            particle.lon = lon
            particle.alt = alt
            particle.current_fitness = fitness

        # Fitness güncellemesi ve pbest kontrolü
        self._evaluate_fitness(particle, fitness)

        return particle

    def remove_particle(self, drone_id: str) -> bool:
        if drone_id in self.particles:
            del self.particles[drone_id]
            return True
        return False

    def _evaluate_fitness(self, p: SwarmParticleState, raw_fitness: float):
        """
        Ham yangın skorunu coğrafi kısıtlar (kapatılmış alan cezaları) ile birleştirerek
        pbest ve gbest durumunu günceller.
        """
        # Yasaklı/kapatılmış alan cezası
        penalty = self.geofence_mgr.get_fitness_penalty(p.lat, p.lon, p.alt)
        effective_fitness = min(1.0, max(0.0, raw_fitness - penalty)) if math.isfinite(raw_fitness) else 0.0
        p.current_fitness = effective_fitness

        # Kişisel en iyi (pbest) güncelleme
        if effective_fitness > p.pbest_fitness:
            p.pbest_fitness = effective_fitness
            p.pbest_lat = p.lat
            p.pbest_lon = p.lon
            p.pbest_alt = p.alt
            if effective_fitness > 0.3:
                p.total_detections += 1

        # Küresel en iyi (gbest) güncelleme
        if effective_fitness > self.gbest_fitness:
            self.gbest_fitness = effective_fitness
            self.gbest_lat = p.lat
            self.gbest_lon = p.lon
            self.gbest_alt = p.alt
            self.gbest_drone_id = p.drone_id

            # Yangın kümesine ekle / güncelle
            self.gbest_timestamp = self.elapsed_seconds

    def _update_fire_cluster(self, lat: float, lon: float, fitness: float, source: str = "camera"):
        """Tespit edilen yangın noktalarını coğrafi küme olarak kaydeder."""
        cos_lat = math.cos(math.radians(lat))
        m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

        # Mevcut kümelerden birine yakın mı (50 metre yarıçap)?
        for cluster in self.discovered_fire_clusters:
            clat = cluster["lat"]
            clon = cluster["lon"]
            d_lat_m = (lat - clat) * self.METERS_PER_DEGREE
            d_lon_m = (lon - clon) * m_per_deg_lon
            dist_m = math.hypot(d_lat_m, d_lon_m)

            if dist_m < 50.0:
                if cluster.get("status") in ("confirmed", "dismissed", "resolved"):
                    return cluster
                cluster["confidence"] = max(cluster["confidence"], fitness)
                cluster["detections_count"] += 1
                return cluster

        # Yeni yangın odağı
        self.discovered_fire_clusters.append({
            "id": f"fire_{len(self.discovered_fire_clusters) + 1}",
            "lat": lat,
            "lon": lon,
            "confidence": fitness,
            "detections_count": 1,
            "verified": False,
            "kind": self.mission_kind,
            "source": source,
            "status": "candidate",
            "created_monotonic": self.elapsed_seconds
        })

        return self.discovered_fire_clusters[-1]

    def _build_routes(self, particles):
        """Persistent boustrophedon lanes; PSO only exploits actual positive evidence."""
        if not particles:
            return
        if self.aoi_bounds is None:
            lat = sum(p.lat for p in particles) / len(particles)
            lon = sum(p.lon for p in particles) / len(particles)
            self.set_aoi(lat - .005, lat + .005, lon - .006, lon + .006)
        key = (tuple(sorted(p.drone_id for p in particles)), tuple(self.aoi_bounds.values()), repr(self.capabilities))
        if key == self._route_key:
            return
        self._route_key = key
        self.detours.clear()
        b = self.aoi_bounds
        lat0, lat1 = b["min_lat"], b["max_lat"]
        lon0, lon1 = b["min_lon"], b["max_lon"]
        margin_y = min(40 / self.METERS_PER_DEGREE, (lat1-lat0) / 4)
        scale_x = self.METERS_PER_DEGREE * math.cos(math.radians((lat0+lat1)/2))
        def capacity(p):
            c = self.capabilities.get(p.drone_id, {})
            height = min(c.get("search_altitude_m", self.config.search_altitude), c.get("max_altitude_m", 120))
            return c.get("max_speed_ms", 10)*height*math.tan(math.radians(c.get("camera_hfov_deg",84)/2))
        total_capacity = sum(capacity(p) for p in particles)
        offset = lon0
        for i, p in enumerate(sorted(particles, key=lambda p: p.drone_id)):
            band = (lon1-lon0)*capacity(p)/total_capacity
            margin_x = min(40 / scale_x, band / 4)
            left, right = offset+margin_x, offset+band-margin_x
            self.sectors[p.drone_id] = [[lat0, offset], [lat1, offset+band]]
            offset += band
            # 70% overlap-aware spacing of the nominal nadir footprint.
            cap = self.capabilities.get(p.drone_id, {})
            height = min(cap.get("search_altitude_m", self.config.search_altitude), cap.get("max_altitude_m", 120))
            spacing = 2*height*math.tan(math.radians(cap.get("camera_hfov_deg",84)/2))*.7
            lanes = max(2, min(500, math.ceil((right-left)*scale_x / max(5, spacing))))
            route = []
            for j in range(lanes):
                x = left+(right-left)*j/max(1, lanes-1)
                ends = [lat0+margin_y, lat1-margin_y]
                if (j+i) % 2:
                    ends.reverse()
                route.extend((y, x) for y in ends)
            self.routes[p.drone_id] = route
            self.route_indices[p.drone_id] = 0

    def step(self, active_ids=None) -> Dict[str, Tuple[float, float, float, float]]:
        self.elapsed_seconds += self.config.dt
        particles = [p for p in self.particles.values() if active_ids is None or p.drone_id in active_ids]
        self._build_routes(particles)
        targets = {}
        if self.gbest_fitness > 0 and self.elapsed_seconds-self.gbest_timestamp > 30:
            self.reset_gbest()
        inspectors = set()
        candidates = [c for c in self.discovered_fire_clusters
                      if c.get("status") == "candidate"
                      and self.elapsed_seconds-c["created_monotonic"] < 30]
        evidence_target = None
        if candidates:
            c = max(candidates, key=lambda c: c["confidence"])
            evidence_target = (c["lat"], c["lon"])
        elif self.gbest_fitness > .3 and not self.discovered_fire_clusters:
            evidence_target = (self.gbest_lat, self.gbest_lon)
        if evidence_target:
            ranked = sorted(particles, key=lambda p: math.hypot(
                p.lat-evidence_target[0], (p.lon-evidence_target[1])*math.cos(math.radians(p.lat))))
            inspectors = {p.drone_id for p in ranked[:min(2, len(particles))]}
        for p in particles:
            scale = self.METERS_PER_DEGREE * math.cos(math.radians(p.lat))
            route = self.routes[p.drone_id]
            idx = self.route_indices[p.drone_id] % len(route)
            target = route[idx]
            inspect = p.drone_id in inspectors
            if inspect:
                target = evidence_target
            dx, dy = (target[1]-p.lon)*scale, (target[0]-p.lat)*self.METERS_PER_DEGREE
            distance = math.hypot(dx, dy)
            if not inspect and distance < 12:
                self.route_indices[p.drone_id] = (idx+1) % len(route)
                target = route[(idx+1) % len(route)]
                dx, dy = (target[1]-p.lon)*scale, (target[0]-p.lat)*self.METERS_PER_DEGREE
                distance = math.hypot(dx, dy)
            self.roles[p.drone_id] = "inspect" if inspect else "search"
            key = (tuple(target), tuple((z.id,tuple(z.coordinates),z.min_alt,z.max_alt) for z in self.geofence_mgr.get_all_zones()))
            cached = self.detours.get(p.drone_id)
            if cached and cached[0] == key:
                path = cached[1]
                if path and math.hypot((path[0][0]-p.lat)*self.METERS_PER_DEGREE, (path[0][1]-p.lon)*scale) < 8:
                    path.pop(0)
            else:
                path = plan_detour(self.geofence_mgr,(p.lat,p.lon),target,p.alt,self.aoi_bounds)
                self.detours[p.drone_id] = (key,path)
            if path:
                target = path[0]
                dx, dy = (target[1]-p.lon)*scale, (target[0]-p.lat)*self.METERS_PER_DEGREE
                distance = math.hypot(dx,dy)
            else:
                dx = dy = distance = 0.0
                self.roles[p.drone_id] = "blocked"
                if not inspect:
                    self.route_indices[p.drone_id] = (idx+1) % len(route)
            self.waypoints[p.drone_id] = list(target)
            # Arrival controller in metres; no forced minimum speed near a target.
            speed = min(6 if inspect else 10, self.capabilities.get(p.drone_id, {}).get("max_speed_ms", 10), self.config.max_speed, distance*.35)
            vx, vy = (dx/max(distance, .001)*speed, dy/max(distance, .001)*speed)
            # Constrained PSO velocity update in BOTH patrol and inspection modes.
            # No evidence => cognitive/social attraction is zero, avoiding false
            # attraction to spawn. A coverage term supplies unexplored objectives.
            r1, r2 = random.random(), random.random()
            cx = (p.pbest_lon-p.lon)*scale if inspect and p.pbest_fitness > .3 else 0
            cy = (p.pbest_lat-p.lat)*self.METERS_PER_DEGREE if inspect and p.pbest_fitness > .3 else 0
            social_x, social_y = (vx,vy) if inspect else (0.0,0.0)
            coverage_x, coverage_y = (0.0,0.0) if inspect else (.5*vx,.5*vy)
            vx = self.config.inertia_weight*p.vx + self.config.cognitive_coeff*r1*max(-2,min(2,cx*.05)) + self.config.social_coeff*r2*social_x + coverage_x
            vy = self.config.inertia_weight*p.vy + self.config.cognitive_coeff*r1*max(-2,min(2,cy*.05)) + self.config.social_coeff*r2*social_y + coverage_y
            for other in particles:
                if other.drone_id == p.drone_id:
                    continue
                ex = (p.lon-other.lon)*scale
                ey = (p.lat-other.lat)*self.METERS_PER_DEGREE
                dist = math.hypot(ex, ey)
                if dist < self.config.safe_drone_distance_m * 2.5:
                    if dist < .1:
                        ex, ey, dist = (-1 if p.drone_id < other.drone_id else 1), 0, 1
                    strength = min(20, (self.config.safe_drone_distance_m*2.5-dist)*.6)
                    vx += ex/dist*strength
                    vy += ey/dist*strength
            target_alt = self.config.inspect_altitude if inspect else self.capabilities.get(p.drone_id, {}).get("search_altitude_m", self.config.search_altitude)
            target_alt = min(target_alt, self.capabilities.get(p.drone_id, {}).get("max_altitude_m", 120))
            target_alt = max(self.config.min_altitude, min(self.config.max_altitude, target_alt))
            vz = max(-2, min(2, (target_alt-p.alt)*.5))
            # Apply a time-based acceleration bound (not a per-frame random change).
            dvx, dvy = vx-p.vx, vy-p.vy
            delta = math.hypot(dvx, dvy)
            factor = min(1, 2.5*self.config.dt/max(delta, .0001))
            vx, vy = p.vx+dvx*factor, p.vy+dvy*factor
            mag = math.hypot(vx, vy)
            maximum = min(self.config.max_speed, self.capabilities.get(p.drone_id, {}).get("max_speed_ms", 10))
            if mag > maximum:
                vx, vy = vx/mag*maximum, vy/mag*maximum
            # Check complete stopping segment, not just a waypoint's endpoint.
            horizon = max(1, mag/2.5 + self.config.dt)
            end_lat = p.lat+vy*horizon/self.METERS_PER_DEGREE
            end_lon = p.lon+vx*horizon/scale
            if not self.geofence_mgr.path_is_clear(p.lat, p.lon, end_lat, end_lon, p.alt):
                vx = vy = 0.0
                if not inspect:
                    self.route_indices[p.drone_id] = (idx+1) % len(route)
                self.roles[p.drone_id] = "blocked"
            if self.aoi_bounds:
                b = self.aoi_bounds
                if not b["min_lat"] <= end_lat <= b["max_lat"]:
                    vy = max(-3, min(3, ((b["min_lat"]+b["max_lat"])/2-p.lat)*self.METERS_PER_DEGREE*.1))
                if not b["min_lon"] <= end_lon <= b["max_lon"]:
                    vx = max(-3, min(3, ((b["min_lon"]+b["max_lon"])/2-p.lon)*scale*.1))
            if not self.geofence_mgr.path_is_clear(p.lat, p.lon,
                    p.lat+vy*horizon/self.METERS_PER_DEGREE, p.lon+vx*horizon/scale, p.alt):
                vx = vy = 0.0
            p.vx, p.vy, p.vz = vx, vy, vz
            p.optimal_altitude = target_alt
            targets[p.drone_id] = (vx, vy, vz, target_alt)
        return targets

    def reset_gbest(self):
        """Kullanıcı bir yangını söndürdüğünde veya bölgeyi kapattığında gbest sıfırlanabilir."""
        self.gbest_fitness = 0.0
        self.gbest_drone_id = None
        for p in self.particles.values():
            p.pbest_fitness = 0.0
