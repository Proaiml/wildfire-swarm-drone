"""
Property and Invariant Tests (Rule 46 Verification)
Kritik sistem değişmezlerini (invariants) matematiksel ve mantıksal olarak garanti eder.
"""

import pytest
import math
from src.safety.safety_plane import SafetyFlightPlane
from src.safety.battery_failsafe import BatteryEnergyModel
from src.communication.membership import SwarmMembershipManager, DroneCapabilities
from src.incidents.incident_manager import FireIncidentManager
from src.perception.fusion import SpatialTemporalEvidenceFusion, DroneObservation
from src.drones.state import DroneState


def test_invariant_safety_no_fly_zone_containment():
    """INVARIANT: Güvenlik Düzlemi hiçbir koşulda NFZ içine hedef waypoint veremez."""
    plane = SafetyFlightPlane()
    nfz = [(37.01, 28.01), (37.01, 28.03), (37.03, 28.03), (37.03, 28.01)]
    plane.add_no_fly_zone(nfz)

    from shapely.geometry import Point, Polygon
    poly = Polygon([(p[1], p[0]) for p in nfz])

    # 100 farklı rastgele aday hedef noktası denenir (içinde olanlar)
    for i in range(100):
        lat = 37.015 + (i % 10) * 0.001
        lon = 28.015 + (i // 10) * 0.001

        safe_lat, safe_lon, safe_alt, _ = plane.validate_and_project_waypoint(
            37.0, 28.0, 50.0, lat, lon, 50.0
        )
        assert not poly.contains(Point(safe_lon, safe_lat)), f"Invariant ihlali: Nokta NFZ içinde! ({safe_lat}, {safe_lon})"


def test_invariant_velocity_limit():
    """INVARIANT: Clamped hız büyüklüğü asla max_speed'i aşamaz."""
    plane = SafetyFlightPlane(max_speed_ms=14.0)
    for vx_raw in [-50.0, -14.0, 0.0, 10.0, 30.0, 100.0]:
        for vy_raw in [-40.0, -10.0, 5.0, 25.0, 80.0]:
            vx, vy, vz = plane.clamp_velocity(vx_raw, vy_raw, 0.0)
            spd = math.hypot(vx, vy)
            assert spd <= 14.001, f"Invariant ihlali: Hız sınırı aşıldı! {spd} > 14.0"


def test_invariant_unique_drone_identity():
    """INVARIANT: Aynı drone_id iki kez aktif register olamaz."""
    mgr = SwarmMembershipManager()
    caps = DroneCapabilities(drone_id="ALPHA_1")
    ok1, _, _ = mgr.process_join_request(caps, 37.0, 28.0)
    assert ok1 is True

    ok2, msg2, _ = mgr.process_join_request(caps, 37.0, 28.0)
    assert ok2 is False
    assert "DUPLICATE_ID" in msg2


def test_invariant_battery_reserve_gate():
    """INVARIANT: Rezerv altındaki drone yeni uzak hedef alamaz, RTL tetiklenir."""
    model = BatteryEnergyModel(safety_margin_percent=20.0)
    drone = DroneState(
        drone_id="B1", lat=37.05, lon=28.05, alt=50.0,
        home_lat=37.00, home_lon=28.00, battery_percentage=18.0,
        is_in_air=True
    )
    must_return, _, _ = model.evaluate_rth_requirement(drone)
    assert must_return is True


def test_invariant_incident_spatial_deduplication():
    """INVARIANT: Aynı yangın koordinatlarında yinelenen incident spam'i oluşamaz."""
    fusion = SpatialTemporalEvidenceFusion()
    mgr = FireIncidentManager(merge_distance_meters=50.0)

    # Aynı konuma 10 farklı drone gözlem bildirsin
    for i in range(10):
        obs = DroneObservation(
            drone_id=f"D_{i}", timestamp=100.0 + i, drone_lat=37.0, drone_lon=28.0, drone_alt=50.0,
            estimated_fire_lat=37.0200, estimated_fire_lon=28.0200, confidence=0.85,
            class_name="fire", box_area_ratio=0.1
        )
        ev = fusion.add_observation(obs)
        if ev:
            mgr.process_evidence(ev)

    assert len(mgr.get_all_incidents()) == 1, "Invariant ihlali: Birden fazla yinelenen incident oluştu!"
