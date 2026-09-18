"""
PyreSwarm - Yangın Olayı Yönetimi ve Yaşam Döngüsü (Fire Incident Management)
Çoklu drone gözlemlerini birleştirerek tekil yangın olaylarına dönüştürür.
Incident Yaşam Döngüsü: CANDIDATE -> SUSPECTED -> CONFIRMED -> MONITORING -> RESOLVED -> EXCLUDED
Aynı yangın için yinelenen (duplicate) incident spam'ini engeller ve operatör kararlarını denetler.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
import time
import math
from src.perception.fusion import FusedEvidence


class IncidentStatus(str, Enum):
    CANDIDATE = "CANDIDATE"       # Tekil veya zayıf ilk kanıt
    SUSPECTED = "SUSPECTED"       # Kararlı, ardışık doğrulanmış kanıt
    CONFIRMED = "CONFIRMED"       # Operatör veya yüksek güvenle (>0.80) onaylanmış yangın
    MONITORING = "MONITORING"     # Aktif olarak drone tarafından izlenen yangın
    RESOLVED = "RESOLVED"         # Söndürülmüş veya kontrol altına alınmış olay
    EXCLUDED = "EXCLUDED"         # Yanlış alarm (false alarm) veya kullanıcı tarafından dışlanan bölge


@dataclass
class FireIncident:
    """Tekil bir yangın olayı veri modeli."""
    incident_id: str
    first_detected_at: float
    last_update: float
    centroid_lat: float
    centroid_lon: float
    confidence: float
    status: IncidentStatus = IncidentStatus.CANDIDATE
    supporting_drones: List[str] = field(default_factory=list)
    supporting_frames: int = 1
    estimated_radius_m: float = 25.0
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[float] = None
    operator_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class FireIncidentManager:
    """
    Sürü genelindeki füzyon kanıtlarını izleyerek yangın olaylarını yönetir.
    """

    def __init__(
        self,
        merge_distance_meters: float = 75.0,
        auto_confirm_threshold: float = 0.85,
        meters_per_degree: float = 111139.0
    ):
        self.merge_distance_m = merge_distance_meters
        self.auto_confirm_threshold = auto_confirm_threshold
        self.meters_per_degree = meters_per_degree

        self._incidents: Dict[str, FireIncident] = {}
        self._incident_counter = 0

    def process_evidence(self, evidence: FusedEvidence) -> FireIncident:
        """
        Gelen füzyon kanıtını uygun bir Incident ile eşleştirir veya yeni bir Incident başlatır.
        """
        now = time.time()
        matched_incident = self._find_matching_incident(evidence.centroid_lat, evidence.centroid_lon)

        if matched_incident is not None:
            # Mevcut incident güncellemesi
            inc = self._incidents[matched_incident]
            # Merkez güncellemesi (Ağırlıklı hareketli ortalama)
            alpha = 0.25
            inc.centroid_lat = round(inc.centroid_lat * (1.0 - alpha) + evidence.centroid_lat * alpha, 6)
            inc.centroid_lon = round(inc.centroid_lon * (1.0 - alpha) + evidence.centroid_lon * alpha, 6)
            inc.confidence = max(inc.confidence, evidence.fused_confidence)
            inc.last_update = now
            inc.supporting_frames += evidence.observation_count

            for d in evidence.reporting_drones:
                if d not in inc.supporting_drones:
                    inc.supporting_drones.append(d)

            # Yaşam döngüsü otomatik terfisi (Eğer henüz operatör müdahalesi yoksa)
            if inc.status in (IncidentStatus.CANDIDATE, IncidentStatus.SUSPECTED):
                if inc.confidence >= self.auto_confirm_threshold and evidence.is_stable:
                    inc.status = IncidentStatus.CONFIRMED
                    inc.confirmed_by = "SYSTEM_AUTO_HIGH_CONFIDENCE"
                    inc.confirmed_at = now
                elif evidence.is_stable or inc.supporting_frames >= 4:
                    inc.status = IncidentStatus.SUSPECTED

            return inc

        # Yeni incident oluştur
        self._incident_counter += 1
        new_id = f"INC-{self._incident_counter:03d}"
        initial_status = IncidentStatus.CANDIDATE
        if evidence.is_stable:
            initial_status = IncidentStatus.SUSPECTED

        new_incident = FireIncident(
            incident_id=new_id,
            first_detected_at=now,
            last_update=now,
            centroid_lat=evidence.centroid_lat,
            centroid_lon=evidence.centroid_lon,
            confidence=evidence.fused_confidence,
            status=initial_status,
            supporting_drones=list(evidence.reporting_drones),
            supporting_frames=evidence.observation_count,
            estimated_radius_m=30.0
        )
        self._incidents[new_id] = new_incident
        return new_incident

    def _find_matching_incident(self, lat: float, lon: float) -> Optional[str]:
        """Verilen koordinata merge_distance_m içinde en yakın aktif incident'ı bulur."""
        best_id = None
        min_dist = float("inf")

        for inc_id, inc in self._incidents.items():
            if inc.status in (IncidentStatus.RESOLVED, IncidentStatus.EXCLUDED):
                continue  # Kapanmış incident'lar ile birleştirme

            d_lat = (lat - inc.centroid_lat) * self.meters_per_degree
            cos_lat = math.cos(math.radians(inc.centroid_lat))
            d_lon = (lon - inc.centroid_lon) * self.meters_per_degree * cos_lat
            dist = math.hypot(d_lat, d_lon)

            if dist <= self.merge_distance_m and dist < min_dist:
                min_dist = dist
                best_id = inc_id

        return best_id

    def confirm_incident(self, incident_id: str, operator_name: str = "OPERATOR") -> bool:
        """Operatör tarafından yangını doğrular."""
        if incident_id not in self._incidents:
            return False
        inc = self._incidents[incident_id]
        inc.status = IncidentStatus.CONFIRMED
        inc.confirmed_by = operator_name
        inc.confirmed_at = time.time()
        inc.last_update = time.time()
        return True

    def mark_false_alarm(self, incident_id: str, operator_name: str = "OPERATOR") -> bool:
        """Operatör tarafından yangını yanlış alarm olarak işaretler ve dışlar."""
        if incident_id not in self._incidents:
            return False
        inc = self._incidents[incident_id]
        inc.status = IncidentStatus.EXCLUDED
        inc.operator_notes = f"Marked FALSE ALARM by {operator_name}"
        inc.last_update = time.time()
        return True

    def resolve_incident(self, incident_id: str, operator_name: str = "OPERATOR") -> bool:
        """Yangın söndürüldü / kontrol altına alındı olarak işaretler."""
        if incident_id not in self._incidents:
            return False
        inc = self._incidents[incident_id]
        inc.status = IncidentStatus.RESOLVED
        inc.operator_notes = f"Resolved by {operator_name}"
        inc.last_update = time.time()
        return True

    def set_monitoring(self, incident_id: str) -> bool:
        """Yangını aktif izleme moduna alır."""
        if incident_id not in self._incidents:
            return False
        inc = self._incidents[incident_id]
        if inc.status in (IncidentStatus.CONFIRMED, IncidentStatus.SUSPECTED):
            inc.status = IncidentStatus.MONITORING
            inc.last_update = time.time()
            return True
        return False

    def get_incident(self, incident_id: str) -> Optional[FireIncident]:
        return self._incidents.get(incident_id)

    def get_all_incidents(self) -> List[FireIncident]:
        return list(self._incidents.values())

    def get_confirmed_incidents(self) -> List[FireIncident]:
        return [
            inc for inc in self._incidents.values()
            if inc.status in (IncidentStatus.CONFIRMED, IncidentStatus.MONITORING)
        ]
