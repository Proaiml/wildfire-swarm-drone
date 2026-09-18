"""
PyreSwarm - 3D PSO Optimizasyon Birim Testleri
"""

import pytest
from core.pso_engine import PSOEngine, PSOConfig
from core.geofence_manager import GeofenceManager


def test_pso_particle_registration():
    pso = PSOEngine()
    p = pso.register_or_update_particle("D1", 37.0500, 28.3200, 50.0, fitness=0.2)
    
    assert "D1" in pso.particles
    assert p.pbest_fitness == 0.2
    assert p.pbest_lat == 37.0500
    assert pso.gbest_fitness == 0.2
    assert pso.gbest_drone_id == "D1"


def test_pso_gbest_sharing():
    pso = PSOEngine()
    # D1 düşük skor buldu
    pso.register_or_update_particle("D1", 37.0500, 28.3200, 50.0, fitness=0.1)
    # D2 yüksek alev skoru buldu
    pso.register_or_update_particle("D2", 37.0550, 28.3250, 50.0, fitness=0.85)

    assert pso.gbest_fitness == 0.85
    assert pso.gbest_drone_id == "D2"
    assert pso.gbest_lat == 37.0550

    # D1 için adım hesaplandığında D1 hızı D2'nin konumuna (gbest) doğru yönelmeli
    commands = pso.step()
    vx, vy, vz, target_alt = commands["D1"]
    
    # D2, D1'in kuzeydoğusundadır (lat ve lon daha büyük). Bu yüzden vx (doğu) ve vy (kuzey) pozitif olmalı
    assert vx > 0
    assert vy > 0
    # Yangın yüksek skorlu olduğu için hedef irtifa alçalmalı (inspect_altitude)
    assert target_alt == pso.config.inspect_altitude


def test_pso_collision_avoidance():
    # İki drone birbirine çok yakın (5 metre)
    cfg = PSOConfig(safe_drone_distance_m=30.0, repulsion_gain=5.0)
    pso = PSOEngine(config=cfg)

    # D1 batıda, D2 hemen doğusunda
    lat = 37.0500
    lon1 = 28.32000
    lon2 = 28.32005 # ~5m mesafe
    
    pso.register_or_update_particle("D1", lat, lon1, 40.0, fitness=0.0)
    pso.register_or_update_particle("D2", lat, lon2, 40.0, fitness=0.0)

    commands = pso.step()
    vx1, _, _, _ = commands["D1"]
    vx2, _, _, _ = commands["D2"]

    # D1 batıya kaçmalı (vx < 0), D2 doğuya kaçmalı (vx > 0)
    assert vx1 < vx2
