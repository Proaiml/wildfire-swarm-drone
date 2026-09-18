"""
PyreSwarm - Uçtan Uca Sürü Entegrasyon ve Simülasyon Testleri
"""

import time
import pytest
from core.swarm_manager import SwarmManager
from core.geofence_manager import ZoneType
from hardware.simulated_drone import SimulatedDrone


def test_swarm_initialization_and_volunteer():
    mgr = SwarmManager(model_path="best.pt", center_lat=37.0500, center_lon=28.3200)

    # 2 Simüle drone ekle
    d1 = SimulatedDrone("D1", 37.0510, 28.3210, initial_alt=30.0)
    d2 = SimulatedDrone("D2", 37.0490, 28.3190, initial_alt=30.0)
    mgr.register_drone(d1)
    mgr.register_drone(d2)

    assert len(mgr.drones) == 2
    assert "D1" in mgr.drones
    assert "D2" in mgr.drones

    # Gönüllü / Vatandaş Drone Ekle (Citizen Drone)
    vol = mgr.register_volunteer("Mehmet K.", 37.0480, 28.3180, alt=25.0)
    assert vol.drone_id in mgr.drones
    assert len(mgr.drones) == 3
    assert vol.pilot_name == "Mehmet K."


def test_swarm_mission_and_fire_convergence():
    # Yangın odağı: 37.0520, 28.3220
    fire_target = (37.0520, 28.3220, 1.0)
    mgr = SwarmManager(model_path="best.pt", center_lat=37.0500, center_lon=28.3200)

    d1 = SimulatedDrone("D1", 37.0518, 28.3219, initial_alt=40.0, fire_targets=[fire_target])
    d2 = SimulatedDrone("D2", 37.0450, 28.3150, initial_alt=40.0, fire_targets=[fire_target])
    mgr.register_drone(d1)
    mgr.register_drone(d2)

    # Görevi başlat
    mgr.start_mission()
    assert mgr.is_mission_active is True

    # Bir tur simülasyon adımı işletelim
    mgr.start()
    time.sleep(1.2)
    mgr.stop()

    state = mgr.get_swarm_state()
    # D1 yangına çok yakın olduğu için kameradan yangın tespit edip gbest'i yükseltmeli
    assert state["drones_count"] == 2
    assert state["gbest"]["fitness"] > 0.0


def test_swarm_close_zone_resets_gbest():
    mgr = SwarmManager(model_path="best.pt", center_lat=37.0500, center_lon=28.3200)
    
    # gbest manuel olarak bir yangın noktasına set edilsin
    mgr.pso.gbest_lat = 37.0550
    mgr.pso.gbest_lon = 28.3250
    mgr.pso.gbest_fitness = 0.9

    # Kullanıcı bu yangının söndürüldüğünü belirterek alanı kapatsın
    closed_coords = [
        (37.0540, 28.3240),
        (37.0560, 28.3240),
        (37.0560, 28.3260),
        (37.0540, 28.3260)
    ]
    mgr.close_zone(
        name="Söndürülen Yangın Alanı",
        zone_type=ZoneType.FIRE_EXTINGUISHED,
        coordinates=closed_coords
    )

    # gbest kapalı alan içinde kaldığı için otomatik sıfırlanmış olmalı
    assert mgr.pso.gbest_fitness == 0.0
