"""Field integration: hybrid search, autopilot control safety, drill timing, API."""
import math
import time
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from core.pso_engine import PSOEngine
from core.swarm_manager import SwarmManager
from hardware.mavlink_drone import MAVLinkDrone, mavutil
from hardware.simulated_drone import SimulatedDrone, SyntheticCamera

M = 111139.0


@pytest.fixture
def manager(monkeypatch):
    detector = Mock(model=None)
    detector.detect.return_value = ([], 0, np.zeros((480, 640, 3), dtype=np.uint8))
    monkeypatch.setattr("core.swarm_manager.FireDetector", lambda **kwargs: detector)
    return SwarmManager(center_lat=37, center_lon=28)


# ---------------------------------------------------------------- search
def engine_with(n=2, strategy="hybrid"):
    p = PSOEngine()
    p.config.search_strategy = strategy
    p.set_aoi(37, 37 + 400 / M, 28, 28 + 400 / (M * math.cos(math.radians(37))))
    for i in range(n):
        p.register_or_update_particle(f"D{i}", 37 + 20 / M, 28 + (50 + 100 * i) / (M * math.cos(math.radians(37))), 60)
    return p


def test_coverage_marks_only_what_the_camera_sees():
    p = engine_with(1)
    p.step()
    cov = p._cov
    seen = cov["last_seen"] == p.elapsed_seconds
    radius = 60 * math.tan(math.radians(42))
    x, y = p._xy(p.particles["D0"].lat, p.particles["D0"].lon)
    dist = np.hypot(cov["x"] - x, cov["y"] - y)
    assert seen.any() and not seen[dist > radius + 1].any()


def test_hybrid_repeats_lanes_until_a_fire_gives_an_ember_zone():
    p = engine_with(2)
    p.set_aoi(37, 37 + 800 / M, 28, 28 + 800 / (M * math.cos(math.radians(37))))
    p.step()
    assert set(p.roles.values()) <= {"search", "inspect"}        # first pass: lanes
    p.sweeps_done["D0"] = 1                                      # D0 finished its sector
    p.step()
    assert p.roles["D0"] == "search"                             # no known fire -> keep sweeping lanes
    p.set_wind(5.0, 225.0)                                       # embers drift north-east
    p._update_fire_cluster(37 + 150 / M, 28 + 150 / (M * math.cos(math.radians(37))), 0.9, source="camera")
    p.discovered_fire_clusters[0]["created_monotonic"] = -100     # evidence already inspected
    p.elapsed_seconds += 120                                      # the cone has not been seen for 2 min
    p.step()
    assert p.roles["D0"] == "ember" and "D0" in p.goals
    assert p.roles["D1"] == "search"


def test_ember_zone_lies_downwind_of_a_known_fire():
    p = engine_with(1)
    p.step()
    p.set_wind(5.0, 225.0)                                       # from south-west -> embers to north-east
    cx, cy = 200.0, 200.0
    lat = 37 + cy / M
    lon = 28 + cx / (M * math.cos(math.radians(37)))
    p._update_fire_cluster(lat, lon, 0.9, source="camera")
    risk = p.ember_risk()
    cov = p._cov
    far = np.hypot(cov["x"] - cx, cov["y"] - cy) > 170          # outside the all-round 150 m spread ring
    ne = risk[far & (cov["x"] > cx) & (cov["y"] > cy)].mean()
    sw = risk[far & (cov["x"] < cx) & (cov["y"] < cy)].mean()
    assert ne > 0 and sw == 0


def test_lane_spacing_follows_the_sensor_reach():
    wide, narrow = engine_with(1, "lanes"), engine_with(1, "lanes")
    narrow.config.sensor_radius_m = 20.0
    wide.step(); narrow.step()
    assert len(narrow.routes["D0"]) > len(wide.routes["D0"])


# ---------------------------------------------------------------- autopilot safety
def fake_autopilot(**kw):
    d = MAVLinkDrone("AP")
    d.master = Mock()
    d.master.mode_mapping.return_value = {"GUIDED": 4, "LOITER": 5, "RTL": 6, "LAND": 9}
    d.autopilot = "ardupilot"
    d.telemetry.last_heartbeat = time.time()
    d.gps_fix, d.gps_sats, d.ekf_flags, d.home = 3, 12, 0x0001 | 0x0002 | 0x0010, (37, 28)
    d.telemetry.battery_percentage = 90
    d.params["FS_GCS_ENABLE"] = 1
    for k, v in kw.items():
        setattr(d, k, v)
    return d


def heartbeat(mode_number, armed=True):
    base = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED | (mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED if armed else 0)
    return SimpleNamespace(type=mavutil.mavlink.MAV_TYPE_QUADROTOR, autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                           base_mode=base, custom_mode=mode_number, system_status=4, mavlink_version=3,
                           get_type=lambda: "HEARTBEAT", get_srcSystem=lambda: 1)


def test_control_refused_until_every_preflight_check_passes():
    d = fake_autopilot(gps_fix=0)
    checks = d.grant_control()
    assert not d.control_enabled and any(c["id"] == "gps" and not c["ok"] for c in checks)
    d.gps_fix = 3
    d.params["FS_GCS_ENABLE"] = 0                   # no failsafe on link loss -> refused
    d.grant_control()
    assert not d.control_enabled
    d.params["FS_GCS_ENABLE"] = 1
    d.grant_control()
    assert d.control_enabled


def test_px4_is_observed_but_not_controlled():
    d = fake_autopilot(autopilot="px4")
    d.grant_control()
    assert not d.control_enabled


def test_pilot_mode_switch_releases_hub_control_at_once():
    d = fake_autopilot()
    d.grant_control()
    d._on_heartbeat(heartbeat(4))                    # GUIDED (hub)
    assert d.control_enabled
    d._on_heartbeat(heartbeat(5))                    # pilot flips to LOITER
    assert not d.control_enabled and d.control_state == "pilot_override"
    assert d.send_velocity(1, 1, 0) is False


def test_hub_commanded_mode_change_is_not_mistaken_for_the_pilot():
    d = fake_autopilot()
    d.grant_control()
    d._on_heartbeat(heartbeat(4))
    d._expected_mode = "RTL"
    d.control_enabled = True
    d._on_heartbeat(heartbeat(6))
    assert d.control_state != "pilot_override"


def test_lost_link_stops_hub_commands(manager):
    d = fake_autopilot()
    d.connect = lambda: True
    manager.register_drone(d)
    d.grant_control()
    d.telemetry.last_heartbeat = time.time() - 10
    manager.tick()
    assert not d.control_enabled and d.control_state == "lost"


def test_pause_and_rtl_reach_controlled_autopilots(manager):
    d = fake_autopilot()
    d.connect = lambda: True
    manager.register_drone(d)
    d.grant_control()
    d.flight_mode = "GUIDED"
    manager.pause_mission()
    assert d.master.mav.set_position_target_local_ned_send.called
    manager.return_to_launch_all()
    assert d.control_state == "rtl" and not d.control_enabled


# ---------------------------------------------------------------- drill timing
def test_drill_records_time_from_ignition_to_detection(manager):
    manager.add_scenario_target(37.001, 28.001, delay_seconds=0)
    manager.pso.elapsed_seconds = 42.0
    manager._score_drill(37.0012, 28.001, "SIM")
    t = manager.scenario_targets[0]
    assert t["detected_s"] == 42.0 and t["delay_s"] == 42.0 and t["detected_by"] == "SIM"


def test_synthetic_drill_camera_shows_fire_only_in_view():
    cam = SyntheticCamera(lambda: [(37.0, 28.0, 0.9)])
    over = SimpleNamespace(is_in_air=True, lat=37.0, lon=28.0, alt=60)
    away = SimpleNamespace(is_in_air=True, lat=37.01, lon=28.0, alt=60)
    assert cam(over, {"camera_hfov_deg": 84}).std() > cam(away, {"camera_hfov_deg": 84}).std()


def test_sim_camera_works_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert SimulatedDrone("S", 37, 28, 0).fire_images


# ---------------------------------------------------------------- API
def test_control_endpoint_reports_failed_checks(monkeypatch, manager):
    import web.app as app_module
    monkeypatch.setattr(app_module, "swarm_mgr", manager)
    d = fake_autopilot(gps_sats=2)
    d.connect = lambda: True
    manager.register_drone(d)
    client = TestClient(app_module.app)
    r = client.post("/api/drone/AP/control", json={"enable": True})
    assert r.status_code == 200 and r.json()["control_enabled"] is False
    assert "GPS 3D fix ve uydu" in r.json()["failed"]
    d.gps_sats = 12
    assert client.post("/api/drone/AP/control", json={"enable": True}).json()["control_enabled"] is True
    assert client.get("/api/drone/AP/preflight").json()["checks"]


def test_two_inspectors_hold_opposite_sides_at_different_heights():
    p = engine_with(3)
    p.step()
    fire = (37 + 200 / M, 28 + 200 / (M * math.cos(math.radians(37))))
    p._update_fire_cluster(*fire, 0.9, source="camera")
    cmds = p.step()
    inspectors = [d for d, r in p.roles.items() if r == "inspect"]
    assert len(inspectors) == 2
    a, b = (p.waypoints[d] for d in inspectors)
    gap = math.hypot((a[0] - b[0]) * M, (a[1] - b[1]) * M * math.cos(math.radians(37)))
    assert gap >= 2 * p.config.inspect_standoff_m - 1
    assert {cmds[d][3] for d in inspectors} == {p.config.inspect_altitude,
                                                  p.config.inspect_altitude + p.config.inspect_alt_step_m}


def test_drill_camera_places_the_fire_where_it_is():
    """Kare heading'e göre döner; algılayıcının piksel->GPS dönüşümü gerçek konumu bulmalı."""
    from hardware.simulated_drone import render_synthetic_frame
    cam = SyntheticCamera(lambda: [])
    fire = (37.0 + 20 / M, 28.0)                                 # 20 m kuzeyde
    for heading, side in ((0, "up"), (90, "left"), (180, "down")):
        frame = render_synthetic_frame(37.0, 28.0, 60, 84, [(fire[0], fire[1], 0.9)], cam.images, cam.texture, heading)
        diff = np.abs(frame.astype(int) - cam.texture.astype(int)).sum(axis=2)
        ys, xs = np.nonzero(diff)
        cy, cx = ys.mean(), xs.mean()
        expect = {"up": cy < 200, "left": cx < 280, "down": cy > 280}[side]
        assert expect, (heading, cx, cy)


def test_frame_and_geolocation_use_the_same_pose(manager):
    """Dönüşte heading ters dönse bile kare, algılamada kullanılan pozdan çizilir."""
    d = SimulatedDrone("S", 37.0, 28.0, 60)
    d.telemetry.is_in_air, d.telemetry.heading = True, 0.0
    d.fire_targets = [(37.0 + 30 / M, 28.0, 0.9)]
    snapshot = SimpleNamespace(lat=37.0, lon=28.0, alt=60.0, heading=0.0)
    d.telemetry.heading = 180.0                                  # drone turned after the snapshot
    frame = d.get_camera_frame(pose=snapshot)
    diff = np.abs(frame.astype(int) - d.forest_texture.astype(int)).sum(axis=2)
    ys, _ = np.nonzero(diff)
    assert ys.mean() < 240                                       # fire drawn ahead, as in the snapshot


def test_drill_does_not_credit_a_neighbouring_fire(manager):
    manager.add_scenario_target(37.0, 28.0, delay_seconds=0)
    manager.add_scenario_target(37.0 + 90 / M, 28.0, delay_seconds=0)      # 90 m north
    manager._ignite_scenario_targets()
    manager.pso.elapsed_seconds = 10.0
    manager._score_drill(37.0 + 5 / M, 28.0, "SIM")                         # sees only the first fire
    a, b = manager.scenario_targets
    assert a["detected_s"] == 10.0 and b.get("detected_s") is None
