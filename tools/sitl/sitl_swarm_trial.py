"""
ArduPilot SITL swarm acceptance trial for PyreSwarm (real ArduCopter flight code).

    docker build -t pyreswarm-sitl tools/sitl
    docker run -d --name pyreswarm-sitl -p 5760-5790:5760-5790 -e COUNT=3 pyreswarm-sitl
    py -3.11 tools/sitl/sitl_swarm_trial.py

What is checked, in order (results -> artifacts/sitl_trial/result.json):
  1. connect      : heartbeat, autopilot type and system id of every vehicle
  2. preflight    : GPS 3D fix, EKF, home, battery, GCS failsafe - control refused until all pass
  3. control      : operator grants hub control; no motion command is ever sent before that
  4. mission      : GUIDED + arm + takeoff, then constrained PSO velocity commands (4 Hz)
  5. drill        : two hidden fires at t=0, one aftershock after 120 s, seen through the
                    synthetic drill camera and the real best.pt model; time to detection
  6. override     : a second MAVLink link switches one vehicle to LOITER (like the pilot's
                    mode switch) -> the hub must release that vehicle at once
  7. link loss    : the hub connection of one vehicle is closed -> the autopilot's own GCS
                    failsafe must take it home (RTL) without the hub
  8. recovery     : remaining vehicles are sent home (RTL) and land
"""
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pymavlink import mavutil  # noqa: E402

from core.swarm_manager import SwarmManager  # noqa: E402
from hardware.mavlink_drone import MAVLinkDrone  # noqa: E402
from hardware.simulated_drone import SyntheticCamera  # noqa: E402

HOME = (37.05637, 30.79052)
SEARCH_ALT = 60.0            # camera footprint radius at 60 m with an 84 deg HFOV: ~54 m
AOI_HALF = (0.0033, 0.0041)  # ~730 m x 730 m search area for three vehicles
PORTS = [5760, 5770, 5780]
OUT = ROOT / "artifacts" / "sitl_trial"
log_lines = []


def log(text):
    line = f"[{time.strftime('%H:%M:%S')}] {text}"
    print(line, flush=True)
    log_lines.append(line)


def separation(manager):
    pts = [(d.telemetry.lat, d.telemetry.lon) for d in manager.drones.values() if d.telemetry.is_in_air]
    best = float("inf")
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            best = min(best, math.hypot((pts[i][0] - pts[j][0]) * 111139,
                                        (pts[i][1] - pts[j][1]) * 111139 * math.cos(math.radians(HOME[0]))))
    return best


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "vehicles": {}, "steps": {}}
    manager = SwarmManager(model_path=str(ROOT / "best.pt"), center_lat=HOME[0], center_lon=HOME[1])
    manager.set_wind(5.0, 225.0)                      # south-west wind: embers drift north-east
    manager.set_aoi(HOME[0] - AOI_HALF[0], HOME[0] + AOI_HALF[0], HOME[1] - AOI_HALF[1], HOME[1] + AOI_HALF[1])

    # 1) connect
    for i, port in enumerate(PORTS):
        drone = MAVLinkDrone(f"SITL-{i + 1}", f"tcp:127.0.0.1:{port}",
                             camera_source=SyntheticCamera(lambda: list(manager.environmental_fires)))
        drone.capabilities.update({"search_altitude_m": SEARCH_ALT, "max_speed_ms": 8.0})
        ok = manager.register_drone(drone)
        log(f"connect {drone.drone_id} tcp:{port}: {'OK' if ok else 'FAILED'} autopilot={drone.autopilot} "
            f"sysid={drone.target_system} mode={drone.flight_mode}")
        result["vehicles"][drone.drone_id] = {"port": port, "connected": ok, "autopilot": drone.autopilot,
                                              "system_id": drone.target_system}
    drones = list(manager.drones.values())
    result["steps"]["connect"] = all(v["connected"] for v in result["vehicles"].values())

    # 2) preflight + 3) control is refused while checks fail, then granted
    manager.start()
    refused_early = manager.set_drone_control(drones[0].drone_id, True)
    result["steps"]["control_refused_before_checks"] = not refused_early["control_enabled"]
    log(f"control before checks refused: {not refused_early['control_enabled']} "
        f"(failed: {refused_early.get('failed')})")
    sent_before = sum(d.last_velocity_sent > 0 for d in drones)
    started = time.time()
    while time.time() - started < 180:
        pending = {d.drone_id: [c["label"] for c in manager.preflight(d.drone_id) if not c["ok"]] for d in drones}
        if not any(pending.values()):
            break
        time.sleep(2)
    log(f"preflight after {time.time() - started:.0f} s: {pending}")
    result["steps"]["preflight_seconds"] = round(time.time() - started, 1)
    for d in drones:
        granted = manager.set_drone_control(d.drone_id, True)
        log(f"grant control {d.drone_id}: {granted['control_enabled']}")
    result["steps"]["no_motion_before_control"] = sent_before == 0
    result["steps"]["control_granted"] = all(d.control_enabled for d in drones)

    # 4) mission + 5) drill
    manager.add_scenario_target(HOME[0] + 0.0012, HOME[1] + 0.0020, 0.95)
    manager.add_scenario_target(HOME[0] - 0.0022, HOME[1] - 0.0025, 0.90)
    # aftershock downwind (north-east) of the first fire, ignites 120 s into the mission
    manager.add_scenario_target(HOME[0] + 0.0027, HOME[1] + 0.0033, 0.92, delay_seconds=120)
    manager.start_mission()
    mission_start = time.time()
    # separation is reported per phase: during takeoff and dispersal the vehicles climb from their
    # own home points (SITL homes are ~25 m apart); "search" starts once every vehicle has been
    # under hub guidance at search altitude for 10 s
    min_sep, min_sep_takeoff, max_speed, samples, tracks = float("inf"), float("inf"), 0.0, [], []
    all_mission_since = None
    while time.time() - mission_start < 360:
        time.sleep(1)
        if manager.is_mission_active:
            airborne = [d for d in drones if d.telemetry.is_in_air]
            if all(d.control_state == "mission" for d in drones):
                all_mission_since = all_mission_since or time.time()
            if len(airborne) >= 2:
                if all_mission_since and time.time() - all_mission_since >= 10:
                    min_sep = min(min_sep, separation(manager))
                else:
                    min_sep_takeoff = min(min_sep_takeoff, separation(manager))
            max_speed = max([max_speed] + [d.telemetry.speed for d in drones])
        tracks.append({"t": round(time.time() - mission_start, 1),
                       "drones": {d.drone_id: [round(d.telemetry.lat, 7), round(d.telemetry.lon, 7),
                                               round(d.telemetry.alt, 1)] for d in drones},
                       "roles": {d.drone_id: [d.control_state, manager.pso.roles.get(d.drone_id)] for d in drones}})
        if int(time.time() - mission_start) % 15 == 0:
            state = {d.drone_id: (d.control_state, d.flight_mode, round(d.telemetry.alt), round(d.telemetry.speed, 1))
                     for d in drones}
            samples.append({"t": round(time.time() - mission_start), "state": state,
                            "incidents": len(manager.pso.discovered_fire_clusters)})
            log(f"t={time.time() - mission_start:4.0f}s {state} incidents={len(manager.pso.discovered_fire_clusters)}")
    drill = [{k: t.get(k) for k in ("id", "aftershock", "ignition_s", "detected_s", "delay_s", "detected_by", "error_m")}
             for t in manager.scenario_targets]
    log(f"drill: {drill}")
    result["steps"]["drill"] = drill
    result["tracks"] = tracks
    result["targets"] = [{k: t[k] for k in ("id", "lat", "lon", "aftershock", "ignition_s")} for t in manager.scenario_targets]
    result["incidents"] = [{k: c[k] for k in ("id", "lat", "lon", "confidence", "created_monotonic")}
                           for c in manager.pso.discovered_fire_clusters]
    result["aoi"] = manager.pso.aoi_bounds
    result["steps"]["min_separation_m"] = round(min_sep, 1)
    result["steps"]["min_separation_takeoff_m"] = round(min_sep_takeoff, 1)
    result["steps"]["max_speed_ms"] = round(max_speed, 1)
    result["steps"]["all_reached_mission"] = all(
        any(s["state"][d.drone_id][0] == "mission" for s in samples) for d in drones)

    # 6) pilot override via a second MAVLink link (like the RC mode switch)
    victim = drones[0]
    pilot = mavutil.mavlink_connection(f"tcp:127.0.0.1:{PORTS[0] + 2}", source_system=200)
    pilot.wait_heartbeat(timeout=10)
    pilot.set_mode(pilot.mode_mapping()["LOITER"])
    t0 = time.time()
    while time.time() - t0 < 10 and victim.control_state != "pilot_override":
        time.sleep(0.1)
    result["steps"]["pilot_override_released_s"] = round(time.time() - t0, 2) if victim.control_state == "pilot_override" else None
    log(f"pilot override: state={victim.control_state} mode={victim.flight_mode} "
        f"after {time.time() - t0:.2f} s, commands still sent: {victim.control_enabled}")

    # 7) hub link loss on vehicle 2 -> autopilot failsafe must bring it home
    lost = drones[1]
    watcher = mavutil.mavlink_connection(f"tcp:127.0.0.1:{PORTS[1] + 2}", source_system=201)
    watcher.wait_heartbeat(timeout=10)
    manager.remove_drone(lost.drone_id)             # closes the hub link (no more GCS heartbeats)
    t0 = time.time()
    mode = None
    while time.time() - t0 < 30:
        hb = watcher.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if hb and hb.type != mavutil.mavlink.MAV_TYPE_GCS:
            mode = mavutil.mode_string_v10(hb)
            if mode in ("RTL", "LAND", "SMART_RTL"):
                break
    result["steps"]["link_loss_failsafe"] = {"mode": mode, "seconds": round(time.time() - t0, 1)}
    log(f"link loss: autopilot switched to {mode} after {time.time() - t0:.1f} s without the hub")

    # 8) recovery
    manager.return_to_launch_all()
    victim.return_to_launch()
    t0 = time.time()
    while time.time() - t0 < 240:
        flying = [d.drone_id for d in (drones[0], drones[2]) if d.telemetry.is_in_air]
        if not flying:
            break
        time.sleep(2)
    result["steps"]["landed_after_rtl_s"] = round(time.time() - t0, 1)
    log(f"recovery: all landed after {time.time() - t0:.0f} s (still flying: {flying})")
    manager.stop()
    result["log"] = log_lines
    (OUT / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"written {OUT / 'result.json'}")


if __name__ == "__main__":
    main()
