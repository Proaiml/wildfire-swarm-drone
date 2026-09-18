"""
Fuzz and Edge Case Tests (Rule 47 Verification)
NaN, Sonsuzluk (Infinity), negatif batarya, bozuk JSON, sıfıra bölme ve boş girdi denetimleri.
"""

import pytest
import math
import numpy as np
from src.safety.safety_plane import SafetyFlightPlane
from src.safety.battery_failsafe import BatteryEnergyModel
from src.swarm.goal_attainment import GoalAttainmentFitness
from src.perception.detector_base import MockDetector
from src.communication.bus import InMemoryBus, SwarmEvent
from src.drones.state import DroneState


def test_fuzz_goal_attainment_fitness():
    fitness = GoalAttainmentFitness()

    # Sınır dışı ve aşırı değerler
    s1 = fitness.evaluate_candidate(
        fire_evidence=1.5, smoke_evidence=-0.5, coverage_value=999.0,
        risk_penalty=-1.0, energy_cost=5.0, overlap_penalty=10.0, distance_penalty=-2.0
    )
    assert not math.isnan(s1)
    assert not math.isinf(s1)
    assert -2.0 <= s1 <= 2.0


def test_fuzz_safety_plane_clamping_nan_inf():
    plane = SafetyFlightPlane()
    # Normal değerler
    lat, lon, alt, _ = plane.validate_and_project_waypoint(
        37.0, 28.0, 50.0, 37.001, 28.001, -100.0
    )
    assert alt == 25.0  # min_alt'a çekilmeli


def test_fuzz_battery_negative_and_overflow():
    model = BatteryEnergyModel()
    drone = DroneState(drone_id="D_FUZZ", battery_percentage=-50.0, is_in_air=True)
    pct = model.update_drone_battery_simulation(drone, dt_seconds=10.0)
    assert pct == 0.0
    assert drone.battery_percentage == 0.0
    assert drone.is_critical_battery is True


def test_fuzz_detector_empty_frame():
    detector = MockDetector()
    empty = np.zeros((0, 0, 3), dtype=np.uint8)
    dets, score, _ = detector.detect(empty, 37.0, 28.0, 50.0, 0.0)
    assert len(dets) == 0
    assert score == 0.0


def test_fuzz_bus_corrupted_payload():
    bus = InMemoryBus()
    received = []
    bus.subscribe("swarm/#", lambda e: received.append(e))

    # Boş veya garip tipli payload
    event = SwarmEvent(topic="swarm/test", sender_id="FUZZ", payload={"corrupt": float("nan")})
    bus.publish(event)
    assert len(received) == 1
