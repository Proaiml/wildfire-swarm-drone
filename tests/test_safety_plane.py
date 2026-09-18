"""
Unit Tests for Safety Flight Plane, Geofence Projection, and APF Collision Avoidance
"""

import pytest
import math
from src.safety.safety_plane import SafetyFlightPlane
from src.safety.collision import CollisionAvoidance
from src.drones.state import DroneState


def test_safety_plane_clamping():
    plane = SafetyFlightPlane(min_altitude_m=30.0, max_altitude_m=100.0, max_speed_ms=12.0)

    # 1. İrtifa sınırları
    _, _, safe_alt_low, mod1 = plane.validate_and_project_waypoint(
        37.0, 28.0, 50.0, 37.0, 28.0, 15.0  # 15m < min_alt
    )
    assert safe_alt_low == 30.0
    assert mod1 is True

    _, _, safe_alt_high, mod2 = plane.validate_and_project_waypoint(
        37.0, 28.0, 50.0, 37.0, 28.0, 150.0  # 150m > max_alt
    )
    assert safe_alt_high == 100.0
    assert mod2 is True

    # 2. Hız sınırları
    vx, vy, vz = plane.clamp_velocity(15.0, 20.0, 5.0)
    speed_2d = math.hypot(vx, vy)
    assert speed_2d <= 12.001
    assert vz <= 4.0


def test_safety_plane_no_fly_zone():
    plane = SafetyFlightPlane()
    # NFZ poligonu
    nfz = [(37.001, 28.001), (37.001, 28.003), (37.003, 28.003), (37.003, 28.001)]
    plane.add_no_fly_zone(nfz)

    # Yasak alanın tam merkezine hedef verilirse
    target_inside_lat = 37.002
    target_inside_lon = 28.002

    safe_lat, safe_lon, safe_alt, was_mod = plane.validate_and_project_waypoint(
        current_lat=37.0, current_lon=28.0, current_alt=50.0,
        target_lat=target_inside_lat, target_lon=target_inside_lon, target_alt=50.0
    )

    assert was_mod is True
    # Güvenli nokta yasak poligonun dışında olmalı
    from shapely.geometry import Point, Polygon
    poly = Polygon([(p[1], p[0]) for p in nfz])
    assert not poly.contains(Point(safe_lon, safe_lat))


def test_apf_collision_avoidance():
    collision = CollisionAvoidance(safe_distance_m=30.0, influence_distance_m=50.0)

    d1 = DroneState(drone_id="D1", lat=37.0, lon=28.0, alt=50.0, is_in_air=True)
    # D2, D1'in 20 metre doğusunda (Tehlikeli yakınlık: 20m < 30m)
    d_lon_20m = 20.0 / (111139.0 * 0.7986)
    d2 = DroneState(drone_id="D2", lat=37.0, lon=28.0 + d_lon_20m, alt=50.0, is_in_air=True)

    fx, fy, fz = collision.calculate_repulsive_force(d1, [d1, d2])
    # D2 doğuda olduğu için D1'i batıya (negatif x) itmeli
    assert fx < 0

    violations = collision.check_swarm_separation_violations([d1, d2])
    assert len(violations) == 1
    assert violations[0]["drone_a"] == "D1"
    assert violations[0]["drone_b"] == "D2"
