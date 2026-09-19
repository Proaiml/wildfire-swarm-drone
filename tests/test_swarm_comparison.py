"""Tests check fairness boundaries, negative controls and measured regressions."""
import numpy as np
from scripts.compare_swarm_search import ObservedMap,optimize,catalog,run_one,summarize,BUDGET


def test_budget_counts_evaluations_not_iterations():
    calls=[]
    def objective(x):calls.append(np.array(x));return float(np.square(x).sum())
    result,n=optimize(catalog()['PSO.OriginalPSO'],objective,101)
    assert n==BUDGET==len(calls)
    assert result.shape==(4,2)


def test_planner_observable_map_has_no_hidden_target_input():
    observed=ObservedMap()
    assert set(vars(observed))=={'last_seen'}
    positions=np.array([[100,100],[300,100],[500,100],[700,100]])
    objective=observed.objective(positions,0)
    assert np.isfinite(objective(np.full(8,300)))
    # Moving a drone after snapshot does not mutate the frozen objective inputs.
    before=objective(np.full(8,300));positions[:]=0
    assert objective(np.full(8,300))==before


def test_disabled_sensor_cannot_magically_find_truth():
    result=run_one('Hub-Constrained-PSO',None,101,horizon=200,sensor_enabled=False)
    assert result['found']==0 and result['recall']==0
    assert result['penalized_delay_s']>0
    assert all(t['detected_s'] is None for t in result['targets'])


def test_separation_regression_random_seed_105():
    result=run_one('Random-waypoints',None,105)
    assert result['minimum_separation_m']>=30  # Previously 28.814 m.
    assert result['bounds_violations']==0


def test_failure_never_becomes_success_or_vanishes():
    failed={'algorithm':'X','seed':1,'status':'failed','error':'deliberate'}
    result=summarize([failed],['X'],[1])
    assert result['failures']==[failed] and result['ranking']==[]
    assert result['completed_runs']==1
