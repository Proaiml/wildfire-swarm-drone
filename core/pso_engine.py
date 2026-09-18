"""
PyreSwarm - 3D Uyarlanabilir Parçacık Sürü Optimizasyon Motoru (PSO Engine)
Yangın tespitinde fiziksel kısıtlar, dinamik irtifa/hız optimizasyonu,
çarpışma önleme (APF) ve kapatılmış alan kaçınması içeren modifiye PSO.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import math
import random
import numpy as np

from core.geofence_manager import GeofenceManager


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
        effective_fitness = max(0.0, raw_fitness - penalty)
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
            self._update_fire_cluster(p.lat, p.lon, effective_fitness)

    def _update_fire_cluster(self, lat: float, lon: float, fitness: float):
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
                cluster["confidence"] = max(cluster["confidence"], fitness)
                cluster["detections_count"] += 1
                return

        # Yeni yangın odağı
        self.discovered_fire_clusters.append({
            "id": f"fire_{len(self.discovered_fire_clusters) + 1}",
            "lat": lat,
            "lon": lon,
            "confidence": fitness,
            "detections_count": 1,
            "verified": fitness > 0.6
        })

    def step(self) -> Dict[str, Tuple[float, float, float, float]]:
        """
        PSO iterasyon adımı: Sürüdeki her parçacık için yeni hedef hızları (vx, vy, vz)
        ve hedef irtifayı hesaplar.
        Döndürür: {drone_id: (target_vx_ms, target_vy_ms, target_vz_ms, target_alt)}
        """
        targets: Dict[str, Tuple[float, float, float, float]] = {}
        dt = self.config.dt
        w = self.config.inertia_weight
        c1 = self.config.cognitive_coeff
        c2 = self.config.social_coeff

        particle_list = list(self.particles.values())

        for p in particle_list:
            cos_lat = math.cos(math.radians(p.lat))
            m_per_deg_lon = self.METERS_PER_DEGREE * cos_lat

            # 1. Bilişsel Bileşen (Cognitive Component - pbest'e çekim)
            r1 = random.random()
            dx_pbest_m = (p.pbest_lon - p.lon) * m_per_deg_lon
            dy_pbest_m = (p.pbest_lat - p.lat) * self.METERS_PER_DEGREE
            dz_pbest_m = p.pbest_alt - p.alt

            cog_vx = c1 * r1 * dx_pbest_m
            cog_vy = c1 * r1 * dy_pbest_m
            cog_vz = c1 * r1 * dz_pbest_m

            # 2. Sosyal Bileşen (Social Component - gbest'e çekim)
            r2 = random.random()
            if self.gbest_fitness > 0.05:
                dx_gbest_m = (self.gbest_lon - p.lon) * m_per_deg_lon
                dy_gbest_m = (self.gbest_lat - p.lat) * self.METERS_PER_DEGREE
                dz_gbest_m = self.config.inspect_altitude - p.alt

                soc_vx = c2 * r2 * dx_gbest_m
                soc_vy = c2 * r2 * dy_gbest_m
                soc_vz = c2 * r2 * dz_gbest_m
            else:
                # Henüz yangın bulunamadıysa: Sürü geniş keşif devriyesi yapar
                soc_vx = 0.0
                soc_vy = 0.0
                soc_vz = 0.0

            # 3. Çarpışma Önleme ve Sürü İçi Ayrılma (Repulsion from Other Drones)
            rep_vx = 0.0
            rep_vy = 0.0
            for other in particle_list:
                if other.drone_id == p.drone_id:
                    continue

                d_x = (p.lon - other.lon) * m_per_deg_lon
                d_y = (p.lat - other.lat) * self.METERS_PER_DEGREE
                dist_m = math.hypot(d_x, d_y)

                if dist_m < self.config.safe_drone_distance_m and dist_m > 0.1:
                    # Ters orantılı itme kuvveti
                    strength = self.config.repulsion_gain * (
                        (self.config.safe_drone_distance_m - dist_m) / self.config.safe_drone_distance_m
                    )
                    angle = math.atan2(d_y, d_x)
                    rep_vx += strength * math.cos(angle)
                    rep_vy += strength * math.sin(angle)

            # 4. Kapatılmış / Yasaklı Alan İtkisi (Geofence Repulsion)
            geo_dlat, geo_dlon = self.geofence_mgr.calculate_repulsion_vector(
                p.lat, p.lon, p.alt, max_repulsion_velocity=self.config.max_speed
            )
            geo_vx = geo_dlon * m_per_deg_lon * self.config.geofence_repulsion_gain
            geo_vy = geo_dlat * self.METERS_PER_DEGREE * self.config.geofence_repulsion_gain

            # 5. Keşif Rüzgarı (Stochastic Exploration)
            exp_vx = (random.random() - 0.5) * 2.0 * self.config.exploration_factor * self.config.max_speed
            exp_vy = (random.random() - 0.5) * 2.0 * self.config.exploration_factor * self.config.max_speed

            # Yeni Hız Vektörü Hesaplama
            new_vx = (w * p.vx) + (cog_vx * 0.3) + (soc_vx * 0.3) + rep_vx + geo_vx + exp_vx
            new_vy = (w * p.vy) + (cog_vy * 0.3) + (soc_vy * 0.3) + rep_vy + geo_vy + exp_vy
            new_vz = (w * p.vz) + (cog_vz * 0.2) + (soc_vz * 0.2)

            # Yatay Hız Limitleri (Saturate)
            speed_2d = math.hypot(new_vx, new_vy)
            if speed_2d > self.config.max_speed:
                new_vx = (new_vx / speed_2d) * self.config.max_speed
                new_vy = (new_vy / speed_2d) * self.config.max_speed
            elif speed_2d < self.config.min_speed:
                # Minimum hareket sağla
                if speed_2d > 0.01:
                    new_vx = (new_vx / speed_2d) * self.config.min_speed
                    new_vy = (new_vy / speed_2d) * self.config.min_speed
                else:
                    new_vx = self.config.min_speed
                    new_vy = 0.0

            # Dikey Hız Limiti
            new_vz = max(-3.0, min(3.0, new_vz))

            # 6. Dinamik İrtifa Adaptasyonu
            # Yangın varsa alçal (detaylı inceleme), yoksa yüksel (geniş görüş açısı)
            if self.gbest_fitness > 0.3:
                target_alt = self.config.inspect_altitude
            else:
                target_alt = self.config.search_altitude

            # Parçacık durumunu güncelle
            p.vx = new_vx
            p.vy = new_vy
            p.vz = new_vz
            p.heading = math.degrees(math.atan2(new_vx, new_vy)) % 360.0
            p.optimal_altitude = target_alt

            targets[p.drone_id] = (new_vx, new_vy, new_vz, target_alt)

        return targets

    def reset_gbest(self):
        """Kullanıcı bir yangını söndürdüğünde veya bölgeyi kapattığında gbest sıfırlanabilir."""
        self.gbest_fitness = 0.0
        self.gbest_drone_id = None
        for p in self.particles.values():
            p.pbest_fitness = 0.0
