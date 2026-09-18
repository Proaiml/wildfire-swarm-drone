"""
Unit Tests for Coordinates and Metric Transformations
"""

import pytest
import math
from src.common.coordinates import (
    geodetic_to_enu,
    enu_to_geodetic,
    haversine_distance,
    enu_distance_2d,
    enu_distance_3d,
    calculate_bearing
)


def test_geodetic_enu_roundtrip():
    ref_lat = 37.0
    ref_lon = 28.0
    ref_alt = 100.0

    target_lat = 37.005
    target_lon = 28.005
    target_alt = 160.0

    e, n, u = geodetic_to_enu(target_lat, target_lon, target_alt, ref_lat, ref_lon, ref_alt)
    assert u == 60.0
    assert e > 0
    assert n > 0

    back_lat, back_lon, back_alt = enu_to_geodetic(e, n, u, ref_lat, ref_lon, ref_alt)
    assert pytest.approx(back_lat, abs=1e-5) == target_lat
    assert pytest.approx(back_lon, abs=1e-5) == target_lon
    assert pytest.approx(back_alt, abs=0.1) == target_alt


def test_haversine_distance():
    lat1, lon1 = 37.0, 28.0
    lat2, lon2 = 37.01, 28.0
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    # 0.01 derece enlem yaklaşık 1111 metre
    assert 1100 < dist < 1120


def test_bearing_calculation():
    # Kuzeye doğru hareket
    b_north = calculate_bearing(37.0, 28.0, 37.01, 28.0)
    assert pytest.approx(b_north, abs=1.0) == 0.0 or pytest.approx(b_north, abs=1.0) == 360.0

    # Doğuya doğru hareket
    b_east = calculate_bearing(37.0, 28.0, 37.0, 28.01)
    assert pytest.approx(b_east, abs=1.0) == 90.0
