"""
Unit Tests for Communication Bus, Loss Watchdog, and Dynamic Swarm Join
"""

import pytest
import time
from src.communication.bus import InMemoryBus, SwarmEvent
from src.communication.loss_handler import CommunicationLossHandler, ConnectionStatus
from src.communication.membership import SwarmMembershipManager, DroneCapabilities


def test_in_memory_bus_wildcard():
    bus = InMemoryBus()
    received = []

    def on_telemetry(evt: SwarmEvent):
        received.append(evt)

    # Joker topic abonesi
    bus.subscribe("swarm/+/drone/+/telemetry", on_telemetry)

    evt1 = SwarmEvent(topic="swarm/alpha/drone/D1/telemetry", sender_id="D1", payload={"battery": 95})
    bus.publish(evt1)

    assert len(received) == 1
    assert received[0].payload["battery"] == 95


def test_communication_loss_watchdog():
    handler = CommunicationLossHandler(
        degraded_threshold_sec=1.0,
        stale_threshold_sec=2.0,
        disconnected_threshold_sec=3.0
    )
    handler.register_drone("D1")
    t0 = time.time()
    handler.record_heartbeat("D1")

    # 1.1 sn sonra DEGRADED
    statuses = handler.audit_all_links(current_time=t0 + 1.1)
    assert statuses["D1"] == ConnectionStatus.DEGRADED

    # 3.5 sn sonra DISCONNECTED
    statuses = handler.audit_all_links(current_time=t0 + 3.5)
    assert statuses["D1"] == ConnectionStatus.DISCONNECTED
    assert "D1" in handler.get_disconnected_drones()


def test_dynamic_swarm_join():
    manager = SwarmMembershipManager(auth_token_secret="TEST_TOKEN")

    caps = DroneCapabilities(
        drone_id="VOLUNTEER_99",
        battery_remaining_pct=90.0,
        max_speed_ms=15.0
    )

    # 1. Geçersiz token ile katılım reddedilmeli
    ok, msg, _ = manager.process_join_request(caps, 37.0, 28.0, auth_token="WRONG_TOKEN")
    assert ok is False
    assert "AUTHENTICATION_FAILED" in msg

    # 2. Geçerli token ile katılım
    ok, msg, drone_state = manager.process_join_request(caps, 37.0, 28.0, auth_token="TEST_TOKEN")
    assert ok is True
    assert drone_state is not None
    assert drone_state.drone_id == "VOLUNTEER_99"

    # 3. Yinelenen (duplicate) katılım reddedilmeli
    ok2, msg2, _ = manager.process_join_request(caps, 37.0, 28.0, auth_token="TEST_TOKEN")
    assert ok2 is False
    assert "DUPLICATE_ID" in msg2
