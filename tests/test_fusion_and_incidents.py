"""
Unit Tests for Perception Fusion and Fire Incident Lifecycle
"""

import pytest
import time
from src.perception.fusion import SpatialTemporalEvidenceFusion, DroneObservation
from src.incidents.incident_manager import FireIncidentManager, IncidentStatus


def test_fusion_evidence_accumulation():
    fusion = SpatialTemporalEvidenceFusion(
        cluster_radius_meters=50.0,
        temporal_window_sec=5.0,
        min_consecutive_detections=3
    )

    t0 = time.time()
    # 1. İlk zayıf gözlem
    obs1 = DroneObservation(
        drone_id="DRONE_01",
        timestamp=t0,
        drone_lat=37.0,
        drone_lon=28.0,
        drone_alt=60.0,
        estimated_fire_lat=37.001,
        estimated_fire_lon=28.001,
        confidence=0.75,
        class_name="fire",
        box_area_ratio=0.10
    )
    ev1 = fusion.add_observation(obs1)
    assert ev1 is not None
    assert ev1.observation_count == 1
    assert not ev1.is_stable  # Henüz 3 gözleme ulaşmadı

    # 2. İkinci gözlem
    obs2 = DroneObservation(
        drone_id="DRONE_01",
        timestamp=t0 + 0.5,
        drone_lat=37.0001,
        drone_lon=28.0001,
        drone_alt=60.0,
        estimated_fire_lat=37.00102,
        estimated_fire_lon=28.00101,
        confidence=0.82,
        class_name="fire",
        box_area_ratio=0.12
    )
    ev2 = fusion.add_observation(obs2)
    assert ev2.observation_count == 2
    assert not ev2.is_stable

    # 3. Üçüncü gözlem (Farklı bir drone)
    obs3 = DroneObservation(
        drone_id="DRONE_02",
        timestamp=t0 + 1.0,
        drone_lat=37.0005,
        drone_lon=28.0005,
        drone_alt=60.0,
        estimated_fire_lat=37.00101,
        estimated_fire_lon=28.00103,
        confidence=0.85,
        class_name="fire",
        box_area_ratio=0.15
    )
    ev3 = fusion.add_observation(obs3)
    assert ev3.observation_count == 3
    assert ev3.is_stable  # 3 gözlem tamamlandı ve güven yüksek
    assert len(ev3.reporting_drones) == 2


def test_incident_lifecycle_and_deduplication():
    manager = FireIncidentManager(merge_distance_meters=70.0, auto_confirm_threshold=0.85)
    fusion = SpatialTemporalEvidenceFusion(min_consecutive_detections=2)

    t0 = time.time()
    obs1 = DroneObservation(
        drone_id="DRONE_01", timestamp=t0, drone_lat=37.0, drone_lon=28.0, drone_alt=60.0,
        estimated_fire_lat=37.002, estimated_fire_lon=28.002, confidence=0.70,
        class_name="fire", box_area_ratio=0.08
    )
    ev1 = fusion.add_observation(obs1)
    inc1 = manager.process_evidence(ev1)
    assert inc1.status == IncidentStatus.CANDIDATE

    # İkinci gözlem ile kararlı hale gelme
    obs2 = DroneObservation(
        drone_id="DRONE_02", timestamp=t0 + 0.5, drone_lat=37.0, drone_lon=28.0, drone_alt=60.0,
        estimated_fire_lat=37.00201, estimated_fire_lon=28.00202, confidence=0.88,
        class_name="fire", box_area_ratio=0.15
    )
    ev2 = fusion.add_observation(obs2)
    inc2 = manager.process_evidence(ev2)
    # Aynı yangın olduğu için tekil incident olmalı
    assert inc2.incident_id == inc1.incident_id
    assert inc2.status in (IncidentStatus.CONFIRMED, IncidentStatus.SUSPECTED)

    # Operatör onayı
    assert manager.confirm_incident(inc1.incident_id, operator_name="COMMANDER")
    assert manager.get_incident(inc1.incident_id).status == IncidentStatus.CONFIRMED

    # Operatör çözüldü yapabilmeli
    assert manager.resolve_incident(inc1.incident_id, operator_name="COMMANDER")
    assert manager.get_incident(inc1.incident_id).status == IncidentStatus.RESOLVED
