"""
PyreSwarm - Saha Operasyonları & Dinamik Sürü Test Paketi
Kalıcı üs yönetimi, dinamik drone konuşlandırma, bireysel kontroller ve batarya fail-safe testleri.
"""

import pytest
from fastapi.testclient import TestClient
from web.app import app, swarm_mgr
from hardware.simulated_drone import SimulatedDrone
from hardware.drone_base import DroneMode


client = TestClient(app)


def test_base_station_get_and_update():
    """Üs konumu alma ve yeni koordinata taşıma testleri."""
    # 1. Mevcut üssü al
    r = client.get("/api/mission/base")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert "lat" in data
    assert "lon" in data
    assert len(data.get("presets", [])) >= 5

    # 2. Üssü Çanakkale Gelibolu koordinatlarına taşı
    new_base = {
        "name": "Çanakkale Gelibolu Orman İleri Üssü",
        "lat": 40.2500,
        "lon": 26.3500,
        "redeploy_drones": True,
        "save_permanent": False,
        "regenerate_fires": True
    }
    r2 = client.post("/api/mission/base", json=new_base)
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["status"] == "success"
    assert res2["lat"] == 40.2500
    assert res2["lon"] == 26.3500
    assert swarm_mgr.base_name == "Çanakkale Gelibolu Orman İleri Üssü"

    # Çevresel yangınlar yeni üsse taşınmış olmalı
    assert len(swarm_mgr.environmental_fires) >= 2
    f_lat, f_lon, _ = swarm_mgr.environmental_fires[0]
    assert abs(f_lat - 40.2500) < 0.01


def test_add_drone_simulated_and_targets():
    """Yeni simüle drone ekleme ve yangın hedeflerini devralma testi."""
    initial_count = len(swarm_mgr.drones)
    req = {
        "drone_id": "TEST-ECHO-99",
        "drone_type": "simulated",
        "spawn_location": "base",
        "alt": 45.0
    }
    r = client.post("/api/swarm/add_drone", json=req)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "success"
    assert res["drone_id"] == "TEST-ECHO-99"
    assert len(swarm_mgr.drones) == initial_count + 1

    # Eklenen drone nesnesini kontrol et
    drone = swarm_mgr.drones["TEST-ECHO-99"]
    assert isinstance(drone, SimulatedDrone)
    assert len(drone.fire_targets) >= 2


def test_single_drone_rtl_and_land():
    """Bireysel drone RTL ve iniş komutları testi."""
    r_rtl = client.post("/api/drone/TEST-ECHO-99/rtl")
    assert r_rtl.status_code == 200
    drone = swarm_mgr.drones["TEST-ECHO-99"]
    assert drone.mode == DroneMode.RTL

    r_land = client.post("/api/drone/TEST-ECHO-99/land")
    assert r_land.status_code == 200
    assert drone.mode == DroneMode.LANDING


def test_drone_removal():
    """Drone'un filodan silinmesi testi."""
    r_del = client.delete("/api/drone/TEST-ECHO-99")
    assert r_del.status_code == 200
    assert "TEST-ECHO-99" not in swarm_mgr.drones

    # Olmayan drone için 404
    r_404 = client.delete("/api/drone/NON_EXISTENT")
    assert r_404.status_code == 404


def test_simulated_drone_low_battery_auto_rtl():
    """Batarya %15 altına düştüğünde otonom RTL fail-safe'inin tetiklenmesi testi."""
    test_drone = SimulatedDrone(
        drone_id="FAILSAFE-01",
        initial_lat=36.8850,
        initial_lon=30.7100,
        initial_alt=40.0
    )
    test_drone.takeoff(target_alt=40.0)
    test_drone.mode = DroneMode.MISSION_PSO
    assert test_drone.mode == DroneMode.MISSION_PSO

    # Bataryayı kritik %14 seviyesine çek ve fizik adımını simüle et
    test_drone.telemetry.battery_percentage = 14.0
    test_drone.update_physics(dt=0.5)

    assert test_drone.telemetry.is_low_battery is True
    assert test_drone.mode == DroneMode.RTL, "Batarya %15 altındayken drone derhal RTL moduna geçmeli!"


def test_quick_fire_generation():
    """Saha hızlı yangın/duman ihbarı oluşturma testi."""
    before_fires = len(swarm_mgr.environmental_fires)
    r = client.post("/api/mission/scenario/quick_fire")
    assert r.status_code == 200
    assert len(swarm_mgr.environmental_fires) == before_fires + 1
