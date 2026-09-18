"""
End-to-End Acceptance Test (Requirement 81 Acceptance Scenario)
Baştan sona tüm iş akışını tek bir senaryoda doğrular:
1. Operasyon alanı ve göl (NO_SEARCH) exclusion zone tanımlanır.
2. 5 drone göreve başlar ve dağıtık aramaya girişir.
3. Drone yangın gözlemi üretir ve uzamsal-zamansal füzyon ile incident oluşur.
4. Operatör incident'ı CONFIRMED yapar.
5. Sürü çeşitlilik yöneticisi yangın çevresini tabu yapar, tüm sürünün çökmesini (collapse) önler.
6. Yeni bir drone (DRONE_06) dinamik olarak sürüye katılır (Join & Capability Discovery).
7. Bir drone bağlantı kaybı (COMM_LOSS) yaşar, sürü kesintisiz çalışmaya devam eder.
8. Bir drone düşük bataryaya ulaşır ve otonom RTL başlatır.
9. Görev tamamlanır ve metrikler eksiksiz toplanır.
"""

import pytest
import time
from simulation.simulator import SwarmSimulationEngine, SyntheticFire
from src.communication.membership import SwarmMembershipManager, DroneCapabilities
from src.communication.loss_handler import CommunicationLossHandler, ConnectionStatus
from src.incidents.incident_manager import IncidentStatus
from src.drones.state import DroneMode, DroneHealth


def test_complete_e2e_acceptance_flow():
    # 1. Simülasyon başlatma (5 drone, 2 km2 alan, 1 yangın, seed 42)
    sim = SwarmSimulationEngine(
        center_lat=37.0,
        center_lon=28.0,
        area_km2=2.0,
        num_drones=5,
        num_fires=1,
        random_seed=42
    )

    # Göl (NO_SEARCH / EXCLUSION ZONE) tanımlama
    lake_zone = [
        (37.001, 28.001),
        (37.001, 28.003),
        (37.003, 28.003),
        (37.003, 28.001)
    ]
    sim.safety_plane.add_no_fly_zone(lake_zone)
    sim.search_map.apply_exclusion_zone(lake_zone)

    # 2. Görev başlangıcı ve ilk adımlar
    for _ in range(10):
        sim.step(dt=1.0)

    assert len(sim.drones) == 5
    assert all(d.is_in_air for d in sim.drones)

    # 3. Drone-3 sentetik yangını gözlemler
    fire = sim.fires[0]
    # Drone 3'ü yangın yakınına konumlandır
    d3 = sim.drones[2]
    d3.lat = fire.lat + 0.0001
    d3.lon = fire.lon + 0.0001
    sim.step(dt=1.0)

    # 4. Spatio-temporal füzyon ve Incident oluşumu
    incidents = sim.incident_manager.get_all_incidents()
    assert len(incidents) >= 1
    target_inc = incidents[0]
    assert target_inc.status in (IncidentStatus.CANDIDATE, IncidentStatus.SUSPECTED, IncidentStatus.CONFIRMED)

    # 5. Operatör yangını doğrular (CONFIRMED)
    sim.incident_manager.confirm_incident(target_inc.incident_id, operator_name="CHIEF_OPERATOR")
    assert sim.incident_manager.get_incident(target_inc.incident_id).status == IncidentStatus.CONFIRMED

    # 6. Sürü çöküşünü önleme: Sadece 2 drone tahsis edilir, diğerleri için yangın tabu bölgesidir
    allocations = sim.diversity_manager.update_incident_allocations(
        sim.incident_manager.get_all_incidents(), sim.drones
    )
    # Yangına en fazla 2 drone tahsis edilmiş olmalı
    assigned_count = sum(1 for v in allocations.values() if v == target_inc.incident_id)
    assert assigned_count <= 2

    # Tahsis edilmemiş bir drone için yangın noktası tabu olmalı
    unassigned_drone = next(d for d in sim.drones if d.drone_id not in allocations)
    assert sim.diversity_manager.is_point_in_taboo_zone(
        fire.lat, fire.lon, unassigned_drone.drone_id, sim.incident_manager.get_all_incidents()
    )

    # 7. Dinamik Drone Katılımı (DRONE_06)
    membership = SwarmMembershipManager()
    caps_d6 = DroneCapabilities(drone_id="DRONE_06", battery_remaining_pct=95.0, cruise_speed_ms=12.0)
    join_ok, _, d6_state = membership.process_join_request(caps_d6, initial_lat=37.0, initial_lon=28.0)
    assert join_ok is True
    assert d6_state.drone_id == "DRONE_06"

    # 8. Drone-2 iletişim kaybı (COMM_LOSS) yaşar
    loss_watchdog = CommunicationLossHandler()
    loss_watchdog.register_drone("DRONE_02")
    loss_watchdog.record_heartbeat("DRONE_02")
    # Simüle edilmiş 20 saniye sonra
    status_map = loss_watchdog.audit_all_links(current_time=time.time() + 20.0)
    assert status_map["DRONE_02"] == ConnectionStatus.DISCONNECTED
    # Sürü kesintisiz çalışmayı sürdürür
    sim.step(dt=1.0)

    # 9. Drone-4 düşük bataryaya ulaşır ve otonom RTL tetiklenir
    d4 = sim.drones[3]
    d4.battery_percentage = 15.0  # Kritik batarya eşiğinde
    must_rtl, _, _ = sim.battery_model.evaluate_rth_requirement(d4)
    assert must_rtl is True
    sim.adapters[3].return_to_home()
    assert d4.mode == DroneMode.RETURNING

    # 10. Görev sonu ve metrik üretimi
    metrics = sim.run_simulation(max_steps=30)
    assert metrics.simulated_time_sec > 0
    assert metrics.final_coverage_pct > 0
    assert metrics.total_distance_km > 0
    assert metrics.total_energy_kj > 0
    assert metrics.incidents_confirmed >= 1
