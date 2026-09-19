"""Actual YOLO inference through production hub, no Mock and no geometric detector."""
import sys, json, math, random, hashlib, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import cv2
from core.swarm_manager import SwarmManager
from hardware.simulated_drone import SimulatedDrone


def main():
    random.seed(2026);np.random.seed(2026)
    out=Path('artifacts/operator_trial');out.mkdir(parents=True,exist_ok=True)
    m=SwarmManager(center_lat=37,center_lon=28)
    if m.detector.model is None:raise RuntimeError('Actual model did not load')
    for i,(lat,lon) in enumerate([(.0015,.001),(-.0015,.0015),(.001,-.0015),(-.001,-.001)]):
        d=SimulatedDrone(f'D{i}',37+lat,28+lon,40);d.telemetry.is_in_air=True;m.register_drone(d)
    m.add_scenario_target(37.0035,28.004)
    m.add_scenario_target(36.997,27.9975)
    m.add_scenario_target(37.001,28.003,delay_seconds=180)
    before=len(m.pso.discovered_fire_clusters)
    assert before==0 and m.pso.gbest_fitness==0
    m.start_mission()
    observations=[];history=[];minimum=1e9
    start=time.perf_counter()
    for step in range(1200):
        m.tick(.5)
        if step%4==0:
            m.perceive_once()
            if m.loop_error:raise RuntimeError(m.loop_error)
            for c in m.pso.discovered_fire_clusters:
                if not any(o['id']==c['id'] for o in observations):observations.append(dict(c))
        drones=list(m.drones.values())
        for i,d in enumerate(drones):
            for other in drones[i+1:]:
                a,b=d.telemetry,other.telemetry
                minimum=min(minimum,math.hypot((a.lat-b.lat)*111139,(a.lon-b.lon)*111139*math.cos(math.radians(37))))
        if step%120==0:
            history.append({'t':m.pso.elapsed_seconds,'drones':m.get_swarm_state()['drones'],'incidents':len(observations)})
            print(f"t={m.pso.elapsed_seconds}: candidates={len(observations)}",flush=True)
            for name,frame in m.latest_annotated_frames.items():cv2.imwrite(str(out/f'{step}_{name}.jpg'),frame)
    result={'seed':2026,'sensor':'Actual best.pt YOLO on simulated photographic frames; no mock',
            'model_sha256':hashlib.sha256(Path('best.pt').read_bytes()).hexdigest(),
            'seconds':600,'wall_seconds':time.perf_counter()-start,'before_start_candidates':before,
            'truth':m.scenario_targets,'candidates':observations,'minimum_separation_m':minimum,'history':history,
            'limitations':['Photos cover full frame; GPS estimates are approximate and cannot establish target identity.',
                           'Not aerial footage or real-flight validation. Synthetic photo bank has known misses.']}
    (out/'trial.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('history','candidates','truth')},indent=2))

if __name__=='__main__':main()
