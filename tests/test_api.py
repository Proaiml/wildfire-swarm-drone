"""
PyreSwarm - FastAPI REST API Birim Testleri
"""

import pytest
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


def test_api_swarm_state():
    response = client.get("/api/swarm/state")
    assert response.status_code == 200
    data = response.json()
    assert "drones" in data
    assert "gbest" in data
    assert "fire_clusters" in data
    assert data["drones_count"] >= 4


def test_api_mission_controls():
    # Başlat
    r_start = client.post("/api/mission/start")
    assert r_start.status_code == 200
    assert r_start.json()["status"] == "success"

    # Duraklat
    r_pause = client.post("/api/mission/pause")
    assert r_pause.status_code == 200
    assert r_pause.json()["status"] == "success"


def test_api_geofence_add_and_delete():
    payload = {
        "name": "Test Kapatılmış Alan",
        "zone_type": "water_body",
        "coordinates": [
            [37.0510, 28.3210],
            [37.0520, 28.3210],
            [37.0520, 28.3220],
            [37.0510, 28.3220]
        ]
    }
    r_add = client.post("/api/geofence/add", json=payload)
    assert r_add.status_code == 200
    res = r_add.json()
    assert res["status"] == "success"
    zone_id = res["zone_id"]

    # Sil
    r_del = client.delete(f"/api/geofence/{zone_id}")
    assert r_del.status_code == 200
    assert r_del.json()["status"] == "success"


def test_api_register_volunteer():
    payload = {
        "pilot_name": "Can Kurtaran",
        "lat": 37.0495,
        "lon": 28.3195,
        "alt": 35.0
    }
    r_vol = client.post("/api/swarm/register_volunteer", json=payload)
    assert r_vol.status_code == 200
    data = r_vol.json()
    assert data["status"] == "success"
    assert "VOLUNTEER" in data["drone_id"]
