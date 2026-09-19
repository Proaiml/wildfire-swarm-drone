"""Regression checks for the actual web/control path, independent of legacy src benchmarks."""
import math
import time
from unittest.mock import Mock
import numpy as np
import pytest
from fastapi.testclient import TestClient
from core.pso_engine import PSOEngine, PSOConfig
from core.swarm_manager import SwarmManager
from core.geofence_manager import GeofenceManager, ZoneType
from hardware.simulated_drone import SimulatedDrone
from hardware.volunteer_bridge import VolunteerDrone
from hardware.drone_base import DroneMode
from core.fire_detector import FireDetector

@pytest.fixture
def manager(monkeypatch):
    detector = Mock(model=None)
    detector.detect.return_value = ([], 0, np.zeros((480,640,3), dtype=np.uint8))
    monkeypatch.setattr('core.swarm_manager.FireDetector', lambda **kwargs: detector)
    return SwarmManager(center_lat=37, center_lon=28)

def add_sim(manager, name='SIM', lat=37, lon=28, alt=40):
    d = SimulatedDrone(name, lat, lon, alt)
    d.telemetry.is_in_air = alt > 0
    manager.register_drone(d)
    return d

def test_initial_scenario_truth_not_incidents(manager):
    add_sim(manager)
    manager.add_scenario_target(37.001, 28.001)
    assert len(manager.environmental_fires) == 1
    assert manager.get_swarm_state()['fire_clusters'] == []
    assert manager.pso.gbest_fitness == 0

def test_candidate_high_confidence_requires_operator(manager):
    c = manager.record_candidate(37,28,.99)
    assert not c['verified'] and c['status'] == 'candidate'
    manager.update_incident(c['id'], 'confirmed')
    assert c['verified']
    manager.update_incident(c['id'], 'resolved')
    manager.record_candidate(37,28,1)
    assert c['status'] == 'resolved' and not c['verified']

def test_second_weaker_incident_is_retained(manager):
    manager.record_candidate(37,28,.99)
    manager.record_candidate(37.003,28.003,.5)
    assert len(manager.pso.discovered_fire_clusters) == 2

def test_mode_isolation_and_no_active_mode_change(manager):
    add_sim(manager)
    manager.record_candidate(37,28,.9)
    manager.set_mission_kind('sar')
    assert manager.get_swarm_state()['fire_clusters'] == []
    manager.add_scenario_target(37,28)
    assert len(manager.sar_targets)==1 and not manager.environmental_fires
    c=manager.record_candidate(37,28,.8)
    assert c['kind']=='sar'
    manager.start_mission()
    with pytest.raises(ValueError): manager.set_mission_kind('fire')

def test_failed_connection_not_registered(manager):
    d=add_sim(manager)
    bad=SimulatedDrone('BAD',37,28)
    bad.connect=Mock(return_value=False)
    assert not manager.register_drone(bad)
    assert 'BAD' not in manager.drones and 'BAD' not in manager.pso.particles
    with pytest.raises(ValueError): manager.register_drone(d)

def test_volunteer_never_fabricates_position_or_freshness():
    d=VolunteerDrone('V','Pilot',37,28,40)
    d.update_from_external(37,28,40,80)
    before=(d.telemetry.lat,d.telemetry.lon,d.telemetry.alt,d.telemetry.last_heartbeat)
    d.send_velocity(10,10,2)
    d.get_telemetry()
    assert before==(d.telemetry.lat,d.telemetry.lon,d.telemetry.alt,d.telemetry.last_heartbeat)
    assert d.get_camera_frame() is None
    assert not d.takeoff()

def test_volunteer_guidance_freshness_and_capabilities(manager):
    d=manager.register_volunteer('Pilot',37,28,40)
    manager.is_mission_active=True
    manager.tick()
    assert d.drone_id not in manager.pso.waypoints
    d.update_from_external(37,28,40,80)
    d.capabilities['max_speed_ms']=3
    for _ in range(30): manager.tick(.25)
    assert d.drone_id in manager.pso.waypoints
    assert math.hypot(d.assigned_target_vx,d.assigned_target_vy) <= 3.0001
    d.telemetry.last_heartbeat=time.time()-10
    manager.tick()
    assert d.assigned_target_vx==d.assigned_target_vy==0

def test_pause_does_not_cancel_rtl_or_landing(manager):
    d=add_sim(manager)
    manager.start_mission()
    d.return_to_launch()
    manager.pause_mission()
    assert d.mode==DroneMode.RTL
    d.land()
    manager.pause_mission()
    assert d.mode==DroneMode.LANDING

def test_physical_bridge_not_silently_commanded(manager):
    d=manager.register_volunteer('Pilot',37,28,40)
    with pytest.raises(ValueError): manager.drone_land(d.drone_id)
    before=(d.telemetry.lat,d.telemetry.lon)
    manager.relocate_swarm(38,29)
    assert before==(d.telemetry.lat,d.telemetry.lon)

def test_takeoff_is_progressive_and_landed_drone_stays_put():
    d=SimulatedDrone('S',37,28,0)
    d.takeoff(30)
    assert d.telemetry.alt==0 and d.mode==DroneMode.TAKEOFF
    d.update_physics(.25)
    assert 0 < d.telemetry.alt < 1
    d.land()
    for _ in range(30): d.update_physics(.25)
    assert not d.telemetry.is_in_air and d.telemetry.alt==0
    lat,lon=d.telemetry.lat,d.telemetry.lon
    d.send_velocity(10,10,3)
    d.update_physics(.25)
    assert (lat,lon)==(d.telemetry.lat,d.telemetry.lon)
    assert d.telemetry.alt==0

def test_control_tick_independent_of_camera(manager):
    d=add_sim(manager)
    d.get_camera_frame=Mock(side_effect=AssertionError('Camera cannot run in flight control'))
    manager.start_mission()
    manager.tick()
    d.get_camera_frame.assert_not_called()

def test_clear_patrol_makes_progress_without_fake_fire(manager):
    d=add_sim(manager)
    manager.start_mission()
    start=(d.telemetry.lat,d.telemetry.lon)
    previous=(0,0)
    for _ in range(240):
        manager.tick(.25)
        v=(d.telemetry.vx,d.telemetry.vy)
        assert math.hypot(v[0]-previous[0],v[1]-previous[1]) <= 2.5*.25+1e-6
        previous=v
    distance=math.hypot((d.telemetry.lat-start[0])*111139,(d.telemetry.lon-start[1])*111139*math.cos(math.radians(start[0])))
    assert distance > 100
    assert not manager.pso.discovered_fire_clusters
    assert abs(d.telemetry.alt-d.capabilities['search_altitude_m']) < 1

def test_evidence_does_not_collapse_entire_swarm(manager):
    for i in range(4):add_sim(manager,f'D{i}',37+i*.001,28+i*.001)
    manager.record_candidate(37,28,.9)
    manager.start_mission();manager.tick()
    assert list(manager.pso.roles.values()).count('inspect')==2
    assert list(manager.pso.roles.values()).count('search')==2

def test_capability_weighted_sectors_partition_aoi():
    p=PSOEngine();p.set_aoi(37,37.01,28,28.01)
    p.register_or_update_particle('A',37.001,28.001,50)
    p.register_or_update_particle('B',37.005,28.005,50)
    p.capabilities={'A':{'max_speed_ms':4},'B':{'max_speed_ms':8}}
    p.step()
    a,b=p.sectors['A'],p.sectors['B']
    assert a[0][1]==28 and b[1][1]==pytest.approx(28.01)
    assert a[1][1]==b[0][1]
    assert (b[1][1]-b[0][1])==pytest.approx(2*(a[1][1]-a[0][1]))

def test_polygon_segment_and_boundary_rejected():
    g=GeofenceManager();g.add_zone('NFZ',ZoneType.NO_FLY_ZONE,[(37,28),(37.001,28),(37.001,28.001),(37,28.001)],safety_margin_meters=0)
    assert not g.path_is_clear(37.0005,27.999,37.0005,28.002,50)
    assert not g.path_is_clear(37,28,37,28.001,50)
    assert g.path_is_clear(36.99,28,36.99,28.001,50)

@pytest.mark.parametrize("mode", [DroneMode.MISSION_PSO, DroneMode.RTL])
def test_crossing_polygon_rejected_in_simulator_including_rtl(mode):
    d=SimulatedDrone('S',37,28,40);d.telemetry.is_in_air=True
    g=GeofenceManager();g.add_zone('NFZ',ZoneType.NO_FLY_ZONE,[(36.9999,28.0001),(37.0001,28.0001),(37.0001,28.0002),(36.9999,28.0002)],safety_margin_meters=2)
    d.geofence_mgr=g;d.mode=mode;d.home_lon=28.002;d.send_velocity(10,0,0)
    for _ in range(60): d.update_physics(.25)
    assert d.telemetry.lon<28.0001 and d.safety_hold

def test_degenerate_geofence_rejected():
    with pytest.raises(ValueError):GeofenceManager().add_zone('bad',ZoneType.NO_FLY_ZONE,[(0,0),(1,1),(0,1),(1,0)])

def test_none_frame_is_safe():
    d=FireDetector(model_path='missing-model.pt')
    assert d.detect(None)==([],0.0,None)

def test_api_validates_input_and_mode(monkeypatch, manager):
    import web.app as web
    monkeypatch.setattr(web,'swarm_mgr',manager)
    client=TestClient(web.app)
    assert client.post('/api/mission/kind',json={'kind':'sar'}).status_code==200
    assert client.post('/api/mission/kind',json={'kind':'unknown'}).status_code==422
    assert client.post('/api/mission/set_aoi',json={'min_lat':38,'max_lat':37,'min_lon':28,'max_lon':29}).status_code==422
    assert client.post('/api/geofence/add',json={'name':'x','zone_type':'typo','coordinates':[[37,28],[37,29],[38,29]]}).status_code==422
    assert client.post('/api/swarm/add_drone',json={'drone_type':'typo'}).status_code==422
    assert client.post('/api/incidents/report',json={'lat':999,'lon':28}).status_code==422
    assert client.post('/api/swarm/add_drone',json={'drone_id':"<script>"}).status_code==422
    assert client.post('/api/mission/start',headers={'origin':'https://untrusted.example'}).status_code==403

def test_api_volunteer_lifecycle(monkeypatch,manager):
    import web.app as web
    monkeypatch.setattr(web,'swarm_mgr',manager);client=TestClient(web.app)
    reply=client.post('/api/swarm/register_volunteer',json={'pilot_name':'Pilot','lat':37,'lon':28,'capabilities':{'max_speed_ms':4}})
    id=reply.json()['drone_id']
    assert client.get(f'/api/volunteer/{id}/guidance').json()['guidance'] is None
    assert client.post(f'/api/volunteer/{id}/telemetry',json={'lat':37,'lon':28,'alt':40,'battery':80,'captured_at':time.time()}).status_code==200
    assert client.post('/api/mission/start').status_code==200
    manager.tick()
    data=client.get(f'/api/volunteer/{id}/guidance').json()
    assert data['advisory_only'] and data['guidance'] and data['waypoint']
    manager.drones[id].telemetry.last_heartbeat=time.time()-10
    assert client.get(f'/api/volunteer/{id}/guidance').json()['guidance'] is None

def test_mavlink_velocity_mapping_and_land():
    from hardware.mavlink_drone import MAVLinkDrone, mavutil
    d=MAVLinkDrone('M');d.master=Mock()
    d.send_velocity(2,3,4,5)
    args=d.master.mav.set_position_target_local_ned_send.call_args.args
    assert args[8:11]==(3,2,-4)
    assert args[4] & (1<<11)==0  # yaw rate is enabled
    d.land()
    d.master.set_mode_rtl.assert_not_called()
    assert d.master.mav.command_long_send.call_args.args[2]==mavutil.mavlink.MAV_CMD_NAV_LAND


def test_sar_synthetic_observation_does_not_use_fire_model(manager):
    d=add_sim(manager)
    manager.set_mission_kind('sar')
    manager.add_scenario_target(37,28)
    manager.detector.detect.side_effect=AssertionError('Fire model is not a person detector')
    manager.perceive_once()
    assert manager.loop_error is None
    assert manager.pso.discovered_fire_clusters[0]['kind']=='sar'
    assert manager.pso.discovered_fire_clusters[0]['source']=='simulation'
    assert not manager.pso.discovered_fire_clusters[0]['verified']
    assert d.telemetry.current_fire_score > 0
    manager.set_mission_kind('fire')
    assert not manager.pso.discovered_fire_clusters


def test_zero_confidence_and_no_video_cannot_create_incident(manager):
    add_sim(manager)
    v=manager.register_volunteer('Pilot',37,28,40)
    v.update_from_external(37,28,40,80)
    manager.perceive_once()
    assert not manager.pso.discovered_fire_clusters
    assert manager.detector.detect.call_count==1


def test_sustained_four_drone_patrol_separation(manager):
    offsets=[(.0015,.001),(-.0015,.0015),(.001,-.0015),(-.001,-.001)]
    for i,(y,x) in enumerate(offsets):add_sim(manager,str(i),37+y,28+x)
    manager.start_mission()
    minimum=1e6
    for _ in range(1200):
        manager.tick(.25)
        drones=list(manager.drones.values())
        for i,a in enumerate(drones):
            for b in drones[i+1:]:
                distance=math.hypot((a.telemetry.lat-b.telemetry.lat)*111139,(a.telemetry.lon-b.telemetry.lon)*111139*math.cos(math.radians(37)))
                minimum=min(minimum,distance)
    assert minimum >= 30, minimum


def test_detour_goes_around_polygon_without_crossing():
    from core.routing import plan_detour
    g=GeofenceManager()
    g.add_zone('Lake',ZoneType.WATER_BODY,[(37,28),(37.001,28),(37.001,28.001),(37,28.001)])
    start=(37.0005,27.998);goal=(37.0005,28.003)
    path=plan_detour(g,start,goal,50)
    assert len(path)>1 and path[-1]==pytest.approx(goal)
    for end in path:
        assert g.path_is_clear(*start,*end,50)
        start=end


def test_no_route_if_drone_enclosed_in_new_exclusion():
    from core.routing import plan_detour
    g=GeofenceManager();g.add_zone('NFZ',ZoneType.NO_FLY_ZONE,[(37,28),(37.001,28),(37.001,28.001),(37,28.001)])
    assert plan_detour(g,(37.0005,28.0005),(37.01,28.01),50)==[]


def test_stale_and_replayed_measurements_rejected():
    d=VolunteerDrone('V','Pilot',37,28,40)
    now=time.time()
    d.update_from_external(37,28,40,80,now)
    with pytest.raises(ValueError):d.update_from_external(38,29,40,80,now)
    with pytest.raises(ValueError):d.update_from_external(38,29,40,80,now-10)
    with pytest.raises(ValueError):d.update_from_external(38,29,40,80,now+20)
    assert d.telemetry.lat==37 and d.telemetry.lon==28


def test_low_battery_returns_before_fixed_threshold_when_far_from_home():
    d=SimulatedDrone('S',37,28,40)
    d.telemetry.is_in_air=True;d.mode=DroneMode.MISSION_PSO
    d.telemetry.lon=28.06;d.telemetry.battery_percentage=40
    d.update_physics(.25)
    assert d.mode==DroneMode.RTL


def test_inspection_expiration_uses_simulation_time(manager):
    add_sim(manager)
    manager.record_candidate(37,28,.9)
    manager.start_mission()
    manager.tick()
    assert manager.pso.roles['SIM']=='inspect'
    for _ in range(125):manager.tick(.25)
    assert manager.pso.roles['SIM']=='search'


def test_pso_social_term_causally_controls_evidence_attraction(monkeypatch):
    monkeypatch.setattr('core.pso_engine.random.random',lambda:.5)
    def command(c2):
        p=PSOEngine(PSOConfig(social_coeff=c2,dt=2))
        p.register_or_update_particle('D',37,28,50)
        p.gbest_lat,p.gbest_lon,p.gbest_fitness=37.002,28.002,.9
        return p.step()['D'][:2]
    disabled=command(0)
    enabled=command(1.65)
    assert disabled==(0,0)
    assert enabled[0]>0 and enabled[1]>0


def test_pso_inertia_affects_patrol_motion(monkeypatch):
    monkeypatch.setattr('core.pso_engine.random.random',lambda:.5)
    def command(w):
        p=PSOEngine(PSOConfig(inertia_weight=w,dt=2))
        drone=p.register_or_update_particle('D',37,28,50)
        drone.vx=2
        return p.step()['D'][0]
    assert command(.8)>command(0)
