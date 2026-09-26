"""Equal-budget, hidden-truth search comparison using installed MEALPY originals.
Not a real-fire detector benchmark. Sensor is explicitly geometric with misses.
Run: py -3.11 scripts/compare_swarm_search.py --seeds 101 102 103

Scenarios (--scenario):
  uniform  : the published setting; every target position is uniform in the area.
  spotting : aftershock (spot) fires ignite DOWNWIND of an initial fire, 150-450 m away
             within +-25 deg of the wind axis (embers). The hub receives the wind as an
             operator input (set_wind); target positions are never given to any planner.

Hub variants:
  Hub-Constrained-PSO : the published lawnmower lanes (lane spacing from the default 85 m
                        camera footprint, wider than the 40 m test sensor).
  Hub-Lanes-Matched   : the same lanes, spacing matched to the 40 m sensor (fairness check).
  Hub-Adaptive-PSO    : the whole swarm revisits the oldest cells (+ ember priority).
  Hub-Hybrid-PSO      : sensor-matched lanes; a drone that has swept its sector once flies to
                        the downwind ember cone of a known fire (cells unseen for >= 60 s),
                        otherwise it repeats its lanes (live default).
"""
import argparse
import importlib
import inspect
import json
import math
import pkgutil
import random
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.pso_engine import PSOEngine
from hardware.simulated_drone import SimulatedDrone
from hardware.drone_base import DroneMode
import mealpy
import mealpy.swarm_based
from mealpy import FloatVar

OUT = Path(__file__).resolve().parents[1] / 'artifacts/swarm_comparison'
M = 111139.0
SX = M * math.cos(math.radians(37))
HORIZON = 600
BUDGET = 200
REPLAN = 30


def catalog(families="swarm"):
    groups = ['swarm_based','evolutionary_based','physics_based','human_based',
              'bio_based','system_based','math_based','music_based']
    if families == "swarm": groups = groups[:1]
    elif families == "others": groups = groups[1:]
    result = {}
    for group in groups:
        package = importlib.import_module('mealpy.' + group)
        for module in pkgutil.iter_modules(package.__path__):
            obj = importlib.import_module(package.__name__ + '.' + module.name)
            for name, cls in inspect.getmembers(obj, inspect.isclass):
                if (name.startswith('Original') or name == 'CMA_ES') and cls.__module__ == obj.__name__:
                    result[module.name + '.' + name] = cls
    return result


class BudgetReached(Exception):
    pass


class ObservedMap:
    """Planner inputs contain only visited cells. No targets or future events."""
    def __init__(self):
        self.last_seen = np.full((20,20), -600.0)

    def observe(self, xy, now):
        axis = np.arange(20)*40+20
        xx, yy = np.meshgrid(axis, axis)
        for point in xy:
            self.last_seen[(xx-point[0])**2+(yy-point[1])**2 <= 40**2] = now

    def objective(self, positions, now):
        ages = np.minimum(300, now-self.last_seen)/300
        positions = positions.copy()
        def score(vector):
            goals = np.asarray(vector).reshape(4,2)
            fractions = np.linspace(.15,1,6)
            path = positions[:,None,:] + (goals-positions)[:,None,:]*fractions[None,:,None]
            cells = np.clip((path/40).astype(int),0,19).reshape(-1,2)
            unique = np.unique(cells, axis=0)
            gain = ages[unique[:,1],unique[:,0]].sum()
            distances = np.linalg.norm(goals-positions,axis=1)
            # Prefer reachable 30-second paths; same proxy for every library method.
            penalty = np.maximum(0,distances-250).sum()/100
            separation = np.linalg.norm(goals[:,None,:]-goals[None,:,:],axis=-1)
            penalty += np.maximum(0,60-separation[np.triu_indices(4,1)]).sum()/30
            return float(-gain + penalty)
        return score


def optimize(cls, objective, seed):
    evaluations = 0
    best = None
    best_score = float('inf')
    def bounded(x):
        nonlocal evaluations, best, best_score
        if evaluations >= BUDGET:
            raise BudgetReached()
        evaluations += 1
        value = objective(x)
        if np.isfinite(value) and value < best_score:
            best_score, best = value, np.array(x).copy()
        return value
    solver = cls(epoch=100, pop_size=50)
    problem = {'bounds': FloatVar(lb=(20.,)*8, ub=(780.,)*8),
               'minmax':'min','obj_func':bounded,'log_to':None}
    initial = np.random.default_rng(seed).uniform(20,780,(50,8))
    try:
        solver.solve(problem, seed=seed, starting_solutions=initial)
    except BudgetReached:
        pass
    if best is None:
        raise RuntimeError('No finite candidate')
    return best.reshape(4,2), evaluations


WIND_SPEED = 5.0


def wind_from_deg(seed):
    return float(np.random.default_rng([seed, 7]).uniform(0, 360))


def scenario(seed, kind='uniform'):
    # Scenarios sampled independently of optimizer seeds and never given to planner.
    rng = np.random.default_rng(seed)
    if kind == 'uniform':
        return [{'xy': rng.uniform(80,720,2).tolist(), 'ignition_s': ignition,
                 'detected_s':None} for ignition in (0,0,180,360)]
    initial = [rng.uniform(80,720,2) for _ in range(2)]
    to = math.radians((wind_from_deg(seed) + 180) % 360)
    targets = [{'xy': xy.tolist(), 'ignition_s': 0, 'detected_s': None} for xy in initial]
    for ignition in (180, 360):
        source = initial[rng.integers(0, 2)]
        angle = to + math.radians(rng.uniform(-25, 25))
        distance = rng.uniform(150, 450)
        xy = np.clip(source + distance * np.array([math.sin(angle), math.cos(angle)]), 60, 740)
        targets.append({'xy': xy.tolist(), 'ignition_s': ignition, 'detected_s': None})
    return targets


def run_one(name, cls, seed, horizon=HORIZON, sensor_enabled=True, scenario_kind='uniform'):
    random.seed(seed)
    engine = PSOEngine()
    engine.aoi_bounds = {'min_lat':37,'max_lat':37+800/M,'min_lon':28,'max_lon':28+800/SX}
    engine.set_wind(WIND_SPEED if scenario_kind == 'spotting' else 0.0, wind_from_deg(seed))
    engine.config.search_strategy = {'Hub-Adaptive-PSO': 'adaptive', 'Hub-Hybrid-PSO': 'hybrid'}.get(name, 'lanes')
    if name in ('Hub-Adaptive-PSO', 'Hub-Hybrid-PSO'):
        engine.config.sensor_radius_m = 40.0            # the planner knows its sensor's reach
    if name == 'Hub-Lanes-Matched':
        # lane spacing = 2 * 85 m * tan(hfov/2) * 0.7 = 2 * 40 m * 0.7 (the test sensor)
        hfov = 2 * math.degrees(math.atan(40 / 85))
        engine.capabilities = {f'D{i}': {'camera_hfov_deg': hfov} for i in range(4)}
    drones = []
    for i,(x,y) in enumerate([(100,100),(300,100),(500,100),(700,100)]):
        drone = SimulatedDrone(f'D{i}',37+y/M,28+x/SX,85)
        drone.mode = DroneMode.MISSION_PSO
        drone.telemetry.is_in_air = True
        drone.telemetry.is_armed = True
        drones.append(drone)
        engine.register_or_update_particle(drone.drone_id,37+y/M,28+x/SX,85)
    truth = scenario(seed, scenario_kind)
    observed = ObservedMap()
    total_evals = 0
    distance = 0.0
    min_separation = 1e9
    speed_max = 0.0
    bounds_violations = 0
    history=[]
    started=time.perf_counter()
    for step in range(int(horizon*2)):
        now=step*.5
        positions=np.array([[(d.telemetry.lon-28)*SX,(d.telemetry.lat-37)*M] for d in drones])
        if step%4==0:
            observed.observe(positions,now)
            # Deterministic Bernoulli outcomes indexed by scenario/time/target/drone.
            # Truth is accessed exclusively here (sensor/evaluator), never in objective.
            for j,target in enumerate(truth):
                if not sensor_enabled or now < target['ignition_s'] or target['detected_s'] is not None:
                    continue
                for i,point in enumerate(positions):
                    if np.linalg.norm(point-np.array(target['xy'])) <= 40:
                        draw=np.random.default_rng(np.random.SeedSequence([seed,j,i,step])).random()
                        if draw >= .2:
                            target['detected_s']=now
                            lat,lon=37+target['xy'][1]/M,28+target['xy'][0]/SX
                            engine._update_fire_cluster(lat,lon,.9,source='synthetic_sensor')
                            break
        if step % (REPLAN*2)==0 and cls is not None:
            goals, count = optimize(cls, observed.objective(positions,now), seed*1000+step)
            total_evals += count
            engine.external_waypoints={f'D{i}':(37+y/M,28+x/SX) for i,(x,y) in enumerate(goals)}
        if name == 'Random-waypoints' and step % (REPLAN*2)==0:
            goals = np.random.default_rng(seed*1000+step).uniform(20,780,(4,2))
            engine.external_waypoints={f'D{i}':(37+y/M,28+x/SX) for i,(x,y) in enumerate(goals)}
        engine.config.dt=.5
        for d in drones:
            t=d.telemetry
            p=engine.particles[d.drone_id]
            p.lat,p.lon,p.alt,p.vx,p.vy,p.vz=t.lat,t.lon,t.alt,t.vx,t.vy,t.vz
        commands=engine.step()
        for d in drones:
            d.send_velocity(*commands[d.drone_id][:3])
            d.update_physics(.5)
            distance+=d.telemetry.speed*.5
            speed_max=max(speed_max,d.telemetry.speed)
        after=np.array([[(d.telemetry.lon-28)*SX,(d.telemetry.lat-37)*M] for d in drones])
        bounds_violations+=int(np.any((after<0)|(after>800)))
        separation=np.linalg.norm(after[:,None,:]-after[None,:,:],axis=-1)
        min_separation=min(min_separation,float(separation[np.triu_indices(4,1)].min()))
        if step%20==0:history.append({'t':now,'xy':after.round(2).tolist()})
    eligible=[t for t in truth if t['ignition_s']<horizon]
    found=[t for t in eligible if t['detected_s'] is not None]
    # Penalized delay assigns every miss the remaining observation window, not deletion.
    delay=np.mean([(t['detected_s'] if t['detected_s'] is not None else horizon)-t['ignition_s'] for t in eligible])
    return {'algorithm':name,'seed':seed,'scenario':scenario_kind,'status':'ok','recall':len(found)/len(eligible),
            'found':len(found),'targets':truth,'penalized_delay_s':float(delay),
            'secondary_recall':sum(t['detected_s'] is not None for t in eligible if t['ignition_s']>0)/max(1,sum(t['ignition_s']>0 for t in eligible)),
            'distance_m':distance,'minimum_separation_m':min_separation,'max_speed_ms':speed_max,
            'bounds_violations':bounds_violations,'evaluations':total_evals,
            'first_detection_s':min((t['detected_s'] for t in truth if t['detected_s'] is not None),default=horizon),
            'secondary_delay_s':float(np.mean([(t['detected_s'] if t['detected_s'] is not None else horizon)-t['ignition_s']
                                               for t in eligible if t['ignition_s']>0])),
            'wall_seconds':time.perf_counter()-started,'history':history}


def summarize(rows, names, seeds):
    ranking=[]
    for name in names:
        group=[r for r in rows if r['algorithm']==name]
        valid=[r for r in group if r['status']=='ok']
        if len(valid)!=len(seeds):continue
        ranking.append({'algorithm':name,'runs':len(valid),
                        'recall':float(np.mean([r['recall'] for r in valid])),
                        'secondary_recall':float(np.mean([r['secondary_recall'] for r in valid])),
                        'penalized_delay_s':float(np.mean([r['penalized_delay_s'] for r in valid])),
                        'secondary_delay_s':float(np.mean([r.get('secondary_delay_s', float('nan')) for r in valid])),
                        'first_detection_s':float(np.mean([min((t['detected_s'] for t in r['targets'] if t['detected_s'] is not None),default=HORIZON) for r in valid])),
                        'minimum_separation_m':min(r['minimum_separation_m'] for r in valid),
                        'safety_pass':all(r['minimum_separation_m'] >=30 and r['bounds_violations']==0 for r in valid),
                        'bounds_violations':sum(r['bounds_violations'] for r in valid)})
    ranking.sort(key=lambda r:(not r['safety_pass'],-r['recall'],r['penalized_delay_s']))
    return {'status':'complete' if len(rows)==len(names)*len(seeds) else 'running',
            'completed_runs':len(rows),'expected_runs':len(names)*len(seeds),
            'mealpy_version':mealpy.__version__,'seeds':seeds,'algorithms':list(names),
            'sensor':'Synthetic 40m radius, 20% false negative, 2s observation. NOT YOLO.',
            'budget_per_replan':BUDGET,'replan_seconds':REPLAN,'horizon_seconds':HORIZON,
            'ranking':ranking,'failures':[{k:v for k,v in r.items() if k!='history'} for r in rows if r['status']!='ok'],
            'limitations':['Screening only, not universal best or flight validation.',
                          'No wind/terrain/radio/battery comparison, no false positives.',
                          'Library methods optimize the same observed coverage proxy; native PSO is an end-to-end reference.',
                          'Safety violations do not disappear from the ranking; inspect them before selection.']}


def write_snapshot(path, payload):
    # FileResponse can read the previous complete snapshot while a run finishes.
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(payload,indent=2), encoding='utf-8')
    for attempt in range(40):
        try:
            temp.replace(path)
            return
        except (PermissionError, OSError):
            if attempt == 39:
                raise
            time.sleep(.05)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds',nargs='+',type=int,default=[101,102,103])
    parser.add_argument('--algorithms',nargs='*')
    parser.add_argument('--output', default=str(OUT))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--families',choices=['swarm','others','all'],default='swarm')
    parser.add_argument('--scenario',choices=['uniform','spotting'],default='uniform')
    args=parser.parse_args()
    output=Path(args.output)
    methods=catalog(args.families)
    methods={'Hub-Hybrid-PSO':None,'Hub-Adaptive-PSO':None,'Hub-Constrained-PSO':None,'Hub-Lanes-Matched':None,
             'Random-waypoints':None,**methods}
    if args.algorithms:methods={n:methods[n] for n in args.algorithms}
    output.mkdir(parents=True,exist_ok=True)
    rows=json.loads((output/'runs.json').read_text(encoding='utf-8')) if args.resume and (output/'runs.json').exists() else []
    completed={(r['algorithm'],r['seed']) for r in rows}
    for name,cls in methods.items():
        for seed in args.seeds:
            if (name,seed) in completed: continue
            try:row=run_one(name,cls,seed,scenario_kind=args.scenario)
            except Exception as exc:row={'algorithm':name,'seed':seed,'status':'failed','error':repr(exc)}
            rows.append(row)
            write_snapshot(output/'runs.json', rows)
            write_snapshot(output/'summary.json', summarize(rows,methods,args.seeds))
            print(json.dumps({k:v for k,v in row.items() if k not in ('history','targets')}),flush=True)

if __name__=='__main__':main()
