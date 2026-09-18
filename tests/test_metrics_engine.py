"""
PyreSwarm - Arama Teorisi ve Matematiksel Metrik Birim Testleri
"""

import math
import pytest
from core.metrics_engine import MetricsEngine, SearchPhysicsConfig


def test_ground_footprint_calculation():
    # 85m irtifa, 84 deg horizontal FOV, 56 deg vertical FOV
    cfg = SearchPhysicsConfig(altitude_m=85.0, horizontal_fov_deg=84.0, vertical_fov_deg=56.0)
    engine = MetricsEngine(cfg)

    w, l, area = engine.get_ground_footprint()
    expected_w = 2.0 * 85.0 * math.tan(math.radians(42.0)) # ~153.07m
    expected_l = 2.0 * 85.0 * math.tan(math.radians(28.0)) # ~90.39m

    assert abs(w - expected_w) < 0.1
    assert abs(l - expected_l) < 0.1
    assert abs(area - (w * l)) < 0.1
    assert area > 13000.0  # ~13,836 m^2


def test_area_coverage_rate():
    cfg = SearchPhysicsConfig(cruise_speed_ms=12.0, overlap_ratio=0.15)
    engine = MetricsEngine(cfg)

    w_eff = engine.get_effective_sweep_width()
    expected_w_eff = 153.07 * 0.85

    assert abs(w_eff - expected_w_eff) < 0.5

    # 5 Drone için ACR hesabı
    acrs = engine.get_area_coverage_rate(num_drones=5)
    assert acrs["effective_sweep_width_m"] > 120.0
    assert acrs["swarm_total_km2h"] > 25.0  # 5 drone saatte 25+ km^2 tarar


def test_analytical_detection_times():
    engine = MetricsEngine()

    # 10 km^2 alan, 4 drone
    res = engine.get_analytical_detection_time(area_km2=10.0, num_drones=4, confidence_percent=95.0)

    assert res["area_km2"] == 10.0
    assert res["num_drones"] == 4
    # 4 drone ile 10 km^2 alanda %50 medyan tespit süresi ~11.4 dk, %95 güven süresi ~49.3 dk'dır
    assert 5.0 < res["t_50_minutes"] < 20.0
    assert 30.0 < res["t_target_conf_minutes"] < 65.0
    # Medyan (%50) süresi %95 süresinden kısa olmalıdır
    assert res["t_50_minutes"] < res["t_target_conf_minutes"]


def test_monte_carlo_benchmark_execution():
    engine = MetricsEngine()
    # Hızlı test için 10 iterasyon
    bench = engine.run_monte_carlo_benchmark(area_km2=4.0, num_drones=3, iterations=10)

    assert "pso" in bench
    assert "random_walk" in bench
    assert "grid_search" in bench
    assert bench["pso"]["mean_minutes"] > 0.0
    # PSO mantıksal olarak rastgele gezinimden daha hızlı olmalı
    assert bench["pso_speedup_vs_random"] >= 1.0
