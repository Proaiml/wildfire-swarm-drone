"""Reproducible actual hub control-path scenario; never a physical flight certificate.
Run: py -3.11 scripts/validate_hub.py
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import math
import random
from unittest.mock import patch,Mock
from core.swarm_manager import SwarmManager
from hardware.simulated_drone import SimulatedDrone
from core.geofence_manager import ZoneType

def run():
    random.seed(2026)
    with patch('core.swarm_manager.FireDetector',return_value=Mock(model=None)):
        manager=SwarmManager(center_lat=37,center_lon=28)
    offsets=[(.0015,.001),(-.0015,.0015),(.001,-.0015),(-.001,-.001)]
    for i,(lat,lon) in enumerate(offsets):
        d=SimulatedDrone(f'D{i}',37+lat,28+lon,40);d.telemetry.is_in_air=True;manager.register_drone(d)
    manager.set_mission_kind('sar')
    manager.add_scenario_target(37.0035,28.004)
    manager.add_scenario_target(36.997,27.9975)
    manager.close_zone('Test exclusion',ZoneType.WATER_BODY,[(37.002,27.997),(37.003,27.997),(37.003,27.998),(37.002,27.998)])
    manager.start_mission()
    minimum=1e9;distance=0;ttfd=None;violations=0;max_speed=0
    history=[]
    for step in range(2400):
        manager.tick(.25)
        if step%8==0: manager.perceive_once()
        if ttfd is None and manager.pso.discovered_fire_clusters:ttfd=step*.25
        drones=list(manager.drones.values())
        for i,a in enumerate(drones):
            t=a.telemetry;distance+=t.speed*.25;max_speed=max(max_speed,t.speed)
            violations+=int(manager.geofence_mgr.is_point_inside(t.lat,t.lon,t.alt)[0])
            for b in drones[i+1:]:
                u=b.telemetry
                minimum=min(minimum,math.hypot((t.lat-u.lat)*111139,(t.lon-u.lon)*111139*math.cos(math.radians(37))))
        if step%40==0:history.append({'t':step*.25,'positions':[[d.telemetry.lat,d.telemetry.lon] for d in drones]})
    result={'scenario':'actual web hub control path / SAR synthetic sensor','seed':2026,'simulated_seconds':600,
            'minimum_separation_m':round(minimum,3),'distance_m':round(distance,1),'max_speed_ms':round(max_speed,3),
            'exclusion_violations':violations,'time_to_first_candidate_s':ttfd,'candidate_count':len(manager.pso.discovered_fire_clusters),
            'operator_confirmed':sum(c['verified'] for c in manager.pso.discovered_fire_clusters),
            'model_used':'SAR geometric synthetic sensor; no person model','hardware_validated':False,
            'history':history}
    out=Path('artifacts/hub_validation');out.mkdir(parents=True,exist_ok=True)
    (out/'scenario.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2))
    assert violations==0
    assert minimum>=30
    assert max_speed<=10.001
    assert result['candidate_count']>=1
    assert result['operator_confirmed']==0

if __name__=='__main__':run()
