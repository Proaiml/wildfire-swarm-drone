"""
PyreSwarm - Uzamsal ve Zamansal Kanıt Füzyonu (Spatial-Temporal Evidence Fusion)
Tekil kare yanılsamalarını (false positives) önlemek amacıyla ardışık kare kanıt birikimi,
üssel düzeltme (EMA) ve çoklu drone uzamsal kümeleme (spatial clustering) uygular.
"""

import time
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from src.perception.detector_base import DetectionResult


@dataclass
class DroneObservation:
    """Tekil bir drone tarafından bildirilen anlık yangın/duman gözlemi."""
    drone_id: str
    timestamp: float
    drone_lat: float
    drone_lon: float
    drone_alt: float
    estimated_fire_lat: float
    estimated_fire_lon: float
    confidence: float
    class_name: str
    box_area_ratio: float
    reliability_weight: float = 1.0  # Drone güvenilirlik/kalibrasyon katsayısı [0.1, 1.0]


@dataclass
class FusedEvidence:
    """Zamansal ve uzamsal olarak kaynaştırılmış yangın hipotezi."""
    cluster_id: str
    centroid_lat: float
    centroid_lon: float
    fused_confidence: float
    first_seen: float
    last_seen: float
    observation_count: int
    reporting_drones: List[str]
    has_fire: bool
    has_smoke: bool
    is_stable: bool  # Ardışık gözlem eşiğini aştı mı?


class SpatialTemporalEvidenceFusion:
    """
    Sürü genelinde gelen gözlemleri uzamsal ve zamansal olarak kaynaştıran füzyon motoru.
    """

    def __init__(
        self,
        cluster_radius_meters: float = 50.0,
        temporal_window_sec: float = 8.0,
        min_consecutive_detections: int = 3,
        confidence_decay_half_life: float = 4.0,
        meters_per_degree: float = 111139.0
    ):
        self.cluster_radius_m = cluster_radius_meters
        self.temporal_window_sec = temporal_window_sec
        self.min_consecutive = min_consecutive_detections
        self.decay_half_life = confidence_decay_half_life
        self.meters_per_degree = meters_per_degree

        # Drone bazlı zamansal geçmiş: drone_id -> List[DroneObservation]
        self._drone_history: Dict[str, List[DroneObservation]] = {}
        # Aktif uzamsal kümeler: cluster_id -> List[DroneObservation]
        self._active_clusters: Dict[str, List[DroneObservation]] = {}
        self._cluster_counter = 0

    def add_observation(self, obs: DroneObservation) -> Optional[FusedEvidence]:
        """
        Yeni bir drone gözlemini sisteme ekler ve güncellenmiş füzyon kanıtını üretir.
        """
        now = obs.timestamp or time.time()
        obs.timestamp = now

        # 1. Drone geçmişine ekle ve bayat verileri temizle
        if obs.drone_id not in self._drone_history:
            self._drone_history[obs.drone_id] = []
        self._drone_history[obs.drone_id].append(obs)
        self._cleanup_stale(now)

        # 2. Uzamsal eşleme (Mevcut kümelerle birleştir veya yeni küme aç)
        assigned_cluster_id = self._match_or_create_cluster(obs)

        # 3. Kümeyi zamansal olarak değerlendir ve füzyon skorunu hesapla
        return self._evaluate_cluster(assigned_cluster_id, now)

    def _match_or_create_cluster(self, obs: DroneObservation) -> str:
        """En yakın kümenin yarıçapı içindeyse dahil et, aksi halde yeni küme başlat."""
        best_cluster_id = None
        min_dist_m = float("inf")

        for c_id, observations in self._active_clusters.items():
            if not observations:
                continue
            # Küme merkezini hesapla
            c_lat = sum(o.estimated_fire_lat for o in observations) / len(observations)
            c_lon = sum(o.estimated_fire_lon for o in observations) / len(observations)

            # Mesafe hesapla (Yerel aproksimasyon)
            d_lat = (obs.estimated_fire_lat - c_lat) * self.meters_per_degree
            cos_lat = math.cos(math.radians(c_lat))
            d_lon = (obs.estimated_fire_lon - c_lon) * self.meters_per_degree * cos_lat
            dist_m = math.hypot(d_lat, d_lon)

            if dist_m <= self.cluster_radius_m and dist_m < min_dist_m:
                min_dist_m = dist_m
                best_cluster_id = c_id

        if best_cluster_id is not None:
            self._active_clusters[best_cluster_id].append(obs)
            return best_cluster_id

        # Yeni küme oluştur
        self._cluster_counter += 1
        new_id = f"CLUST_{self._cluster_counter:04d}"
        self._active_clusters[new_id] = [obs]
        return new_id

    def _evaluate_cluster(self, cluster_id: str, current_time: float) -> FusedEvidence:
        """Kümedeki gözlemlerden ağırlıklı güven skoru ve kararlılık üretir."""
        observations = self._active_clusters.get(cluster_id, [])
        if not observations:
            return FusedEvidence(
                cluster_id=cluster_id, centroid_lat=0.0, centroid_lon=0.0,
                fused_confidence=0.0, first_seen=current_time, last_seen=current_time,
                observation_count=0, reporting_drones=[], has_fire=False, has_smoke=False, is_stable=False
            )

        # Ağırlıklı merkez ve zaman sönümlü (exponential decay) güven skoru
        total_weight = 0.0
        weighted_lat = 0.0
        weighted_lon = 0.0
        weighted_conf = 0.0

        drones_set = set()
        has_fire = False
        has_smoke = False

        for obs in observations:
            dt = max(0.0, current_time - obs.timestamp)
            # Zaman sönümleme faktörü: 2^(-dt / T_half)
            decay = math.pow(0.5, dt / max(0.1, self.decay_half_life))
            w = obs.reliability_weight * decay * (1.0 + 0.5 * math.sqrt(obs.box_area_ratio * 10.0))

            total_weight += w
            weighted_lat += obs.estimated_fire_lat * w
            weighted_lon += obs.estimated_fire_lon * w
            weighted_conf += obs.confidence * w

            drones_set.add(obs.drone_id)
            if "fire" in obs.class_name.lower():
                has_fire = True
            if "smoke" in obs.class_name.lower():
                has_smoke = True

        c_lat = weighted_lat / total_weight if total_weight > 0 else observations[-1].estimated_fire_lat
        c_lon = weighted_lon / total_weight if total_weight > 0 else observations[-1].estimated_fire_lon
        raw_conf = weighted_conf / total_weight if total_weight > 0 else 0.0

        # Çoklu drone bonusu (Farklı drone'lar aynı yeri görüyorsa güven artar)
        diversity_multiplier = 1.0 + 0.15 * min(3, len(drones_set) - 1)
        fused_conf = min(0.99, raw_conf * diversity_multiplier)

        first_seen = min(o.timestamp for o in observations)
        last_seen = max(o.timestamp for o in observations)
        obs_count = len(observations)

        # Kararlılık: En az min_consecutive gözlem ve güven > 0.40
        is_stable = (obs_count >= self.min_consecutive) and (fused_conf >= 0.40)

        return FusedEvidence(
            cluster_id=cluster_id,
            centroid_lat=round(c_lat, 6),
            centroid_lon=round(c_lon, 6),
            fused_confidence=round(fused_conf, 3),
            first_seen=first_seen,
            last_seen=last_seen,
            observation_count=obs_count,
            reporting_drones=list(drones_set),
            has_fire=has_fire,
            has_smoke=has_smoke,
            is_stable=is_stable
        )

    def _cleanup_stale(self, current_time: float):
        """Zaman penceresi dışındaki gözlemleri ve boş kümeleri temizler."""
        cutoff = current_time - self.temporal_window_sec

        for drone_id in list(self._drone_history.keys()):
            self._drone_history[drone_id] = [
                o for o in self._drone_history[drone_id] if o.timestamp >= cutoff
            ]

        for c_id in list(self._active_clusters.keys()):
            self._active_clusters[c_id] = [
                o for o in self._active_clusters[c_id] if o.timestamp >= cutoff
            ]
            if not self._active_clusters[c_id]:
                del self._active_clusters[c_id]

    def get_all_active_hypotheses(self, current_time: Optional[float] = None) -> List[FusedEvidence]:
        """Mevcut tüm aktif kümelenmiş yangın hipotezlerini döndürür."""
        now = current_time or time.time()
        self._cleanup_stale(now)
        hypotheses = []
        for c_id in list(self._active_clusters.keys()):
            h = self._evaluate_cluster(c_id, now)
            if h.observation_count > 0:
                hypotheses.append(h)
        return hypotheses
