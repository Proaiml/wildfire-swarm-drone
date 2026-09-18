"""
PyreSwarm - Ölçeklenebilirlik ve Yüksek Frekans Performans Testleri
"""

import time
import pytest
from core.pso_engine import PSOEngine, PSOConfig
from core.geofence_manager import GeofenceManager


def test_pso_large_swarm_scalability():
    """30 drone'luk bir filoda PSO adım süresi ölçümü."""
    pso = PSOEngine()
    
    # 30 adet drone ekle
    for i in range(30):
        lat = 37.0500 + (i * 0.001)
        lon = 28.3200 + (i * 0.001)
        pso.register_or_update_particle(f"DRONE-{i:02d}", lat, lon, 85.0, fitness=0.0)

    assert len(pso.particles) == 30

    # 100 adım işlet ve toplam süreyi ölç
    start = time.time()
    for _ in range(100):
        commands = pso.step()
        assert len(commands) == 30
    elapsed = time.time() - start

    # Adım başına ortalama süre (10ms'den küçük olmalı)
    avg_step_ms = (elapsed / 100.0) * 1000.0
    print(f"\n[Performance] 30 Drone için PSO Adım Süresi: {avg_step_ms:.2f} ms")
    assert avg_step_ms < 20.0, f"PSO adımı çok yavaş: {avg_step_ms} ms"


def test_pso_zero_drones_graceful():
    """Hiç drone yokken adımın çökmeden boş dönmesi."""
    pso = PSOEngine()
    commands = pso.step()
    assert commands == {}
