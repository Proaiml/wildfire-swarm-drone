"""
Unit Tests for Battery Energy Model and Autonomous Return-to-Home (RTH) Gate
"""

import pytest
from src.safety.battery_failsafe import BatteryEnergyModel
from src.drones.state import DroneState, DroneMode, DroneHealth


def test_battery_discharge_simulation():
    model = BatteryEnergyModel(nominal_capacity_mah=5000.0, power_cruise_w=180.0)
    drone = DroneState(drone_id="D1", battery_percentage=100.0, is_in_air=True)

    # 60 saniye uçuş
    pct = model.update_drone_battery_simulation(drone, dt_seconds=60.0, is_moving=True)
    assert pct < 100.0
    assert drone.battery_voltage < 16.8
    assert drone.health == DroneHealth.HEALTHY


def test_autonomous_rth_gate():
    model = BatteryEnergyModel(safety_margin_percent=20.0)
    # Üsten 2 km uzakta bir drone
    drone = DroneState(
        drone_id="D1",
        lat=37.02, lon=28.0, alt=60.0,
        home_lat=37.00, home_lon=28.0, home_alt=0.0,
        battery_percentage=22.0,  # Kritik eşiğe yakın
        is_in_air=True
    )

    must_rth, time_left, info = model.evaluate_rth_requirement(drone)
    assert must_rth is True
    assert info["must_return_home"] is True
