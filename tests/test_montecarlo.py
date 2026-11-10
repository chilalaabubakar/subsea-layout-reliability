import itertools
import math

import numpy as np

from layout_rel.config import param
from layout_rel.economics import npv_breakdown
from layout_rel.montecarlo import (cvar, default_sizes, sample_scenarios, scenario_cost,
                                   simulate_layout)
from layout_rel.optimizer import optimize_npv

ONE = {w: "M2" for w in ("W1", "W2", "W3", "W4", "W5", "W6")}
SPLIT = {"W1": "M1", "W2": "M1", "W3": "M1", "W4": "M3", "W5": "M3", "W6": "M3"}


def ev_failure_pv(field, cfg, a):
    n = npv_breakdown(field, cfg, a)
    return n["repair_cost"] + n["lost_production"]


def test_cvar_by_hand():
    x = np.arange(1, 101, dtype=float)          # 1..100
    assert math.isclose(cvar(x, 0.95), np.mean([96, 97, 98, 99, 100]))


def test_simulation_is_reproducible(field, cfg):
    a = simulate_layout(field, cfg, ONE, n=200, seed=7).total_pv
    b = simulate_layout(field, cfg, ONE, n=200, seed=7).total_pv
    assert np.array_equal(a, b)


def test_mc_mean_close_to_expected_value(field, cfg):
    # EV ignores overlapping outages, so it should be slightly ABOVE the MC mean
    for a in (ONE, SPLIT):
        ev = ev_failure_pv(field, cfg, a)
        mc = simulate_layout(field, cfg, a, n=5000).total_pv
        assert abs(mc.mean() / ev - 1) < 0.05
        assert mc.mean() < ev * 1.01


def test_scenarios_unbiased_for_expected_value(field, cfg):
    sc = sample_scenarios(field, cfg, n=3000)
    for a in (ONE, SPLIT):
        x = np.array([scenario_cost(c, a, default_sizes(cfg, a)) for c in sc])
        assert abs(x.mean() / ev_failure_pv(field, cfg, a) - 1) < 0.05


def test_cvar_milp_matches_brute_force(field, cfg):
    rho, alpha = 0.6, param(cfg, "risk.alpha")
    sc = sample_scenarios(field, cfg, n=100)
    opex = param(cfg, "economics.opex_fraction_of_capex")
    from layout_rel.economics import annuity_factors
    a_rep = annuity_factors(cfg)[0]
    best = math.inf
    biggest = max(param(cfg, "manifold.sizes"))
    for combo in itertools.product(field.sites, repeat=len(field.wells)):
        if any(combo.count(s) > biggest for s in field.sites):
            continue
        a = dict(zip(field.wells, combo))
        n = npv_breakdown(field, cfg, a)
        x = np.array([scenario_cost(c, a, default_sizes(cfg, a)) for c in sc])
        # sample CVaR exactly as the LP defines it: min over eta
        k = len(x) * (1 - alpha)
        xs = np.sort(x)[::-1]
        tail = xs[: int(math.floor(k))].sum() + (k - math.floor(k)) * xs[int(math.floor(k))]
        cv = tail / k
        cost = n["capex"] * (1 + opex * a_rep) + (1 - rho) * (n["repair_cost"] + n["lost_production"]) + rho * cv
        best = min(best, cost)
    sol = optimize_npv(field, cfg, risk_weight=rho, scenarios=sc)
    assert math.isclose(sol.info["cost_pv"], best, rel_tol=1e-6)


# ---------------------------------------------------------------- weather wait by failure date
def _solveig():
    from layout_rel.config import REPO_ROOT, field_path, load_config
    from layout_rel.layout import load_field
    cfg = load_config(REPO_ROOT / "config" / "solveig_weather.yaml")
    return load_field(field_path(cfg), param(cfg, "routing.length_factor")), cfg


def test_mean_wait_mode_is_unchanged(field, cfg):
    """Without an hourly wait file the simulation is the same as before the file existed."""
    assert param(cfg, "montecarlo.weather_wait_file") is None
    r = simulate_layout(field, cfg, {w: field.sites[0] for w in field.wells}, n=300, seed=1)
    assert math.isclose(r.total_pv.sum(), 63326969854.333664, rel_tol=1e-12)
    assert math.isclose(r.downtime.sum(), 35470607897.685, rel_tol=1e-12)


def test_hourly_waits_keep_the_config_mean_and_are_seasonal():
    from layout_rel.maintenance import repair
    from layout_rel.montecarlo import weather_waits
    from layout_rel.units import DAY, YEAR
    field, cfg = _solveig()
    ww = weather_waits(cfg)
    assert len(ww.year_start) == 10 and ww.year_start[0] == 0
    for kind, w in ww.wait.items():
        assert math.isclose(w.mean(), param(cfg, f"maintenance.{kind}.weather_wait_days"), rel_tol=1e-9)
    r = repair(cfg, "manifold")
    years = np.arange(20) * YEAR
    jan = ww.downtime("manifold", r, years + 15 * DAY - r.mobilisation, 0)      # vessel ready mid-January
    jul = ww.downtime("manifold", r, years + 196 * DAY - r.mobilisation, 0)     # vessel ready mid-July
    assert jan.mean() > 2 * jul.mean()
    assert jul.min() >= r.mobilisation + r.active


def test_sampled_waits_widen_the_spread_but_keep_the_mean():
    import copy
    field, cfg = _solveig()
    fixed = copy.deepcopy(cfg)
    fixed["montecarlo"]["weather_wait_file"]["value"] = None
    a = {w: "M_CEN" for w in field.wells}
    x = simulate_layout(field, cfg, a, {"M_CEN": 6}, n=4000).total_pv
    y = simulate_layout(field, fixed, a, {"M_CEN": 6}, n=4000).total_pv
    assert abs(x.mean() / y.mean() - 1) < 0.05
    assert x.std() > y.std() and cvar(x, 0.95) > cvar(y, 0.95)


def test_enumeration_on_scenarios_matches_cvar_milp(field, cfg):
    from layout_rel.saa import ScenarioArrays, layout_table
    sc = sample_scenarios(field, cfg, n=150, seed=11)
    arr = ScenarioArrays.from_scenarios(field, cfg, sc)
    a, s = SPLIT, default_sizes(cfg, SPLIT)
    assert np.allclose(arr.cost(a, s), [scenario_cost(c, a, s) for c in sc], rtol=1e-12)
    tab = layout_table(field, cfg, arr)
    for w in (0.4, 1.0):
        sol = optimize_npv(field, cfg, risk_weight=w, scenarios=sc)
        assert math.isclose(sol.info["cost_pv"], tab.objective(w).min(), rel_tol=1e-6)


def test_simulation_and_expected_value_agree_with_deferred_production(field, cfg):
    import copy
    c = copy.deepcopy(cfg)
    c["production"]["deferred_fraction"]["value"] = 0.5
    ev, base = ev_failure_pv(field, c, ONE), ev_failure_pv(field, cfg, ONE)
    assert ev < base                                                # deferral lowers the failure cost
    mc = simulate_layout(field, c, ONE, n=5000).total_pv
    assert abs(mc.mean() / ev - 1) < 0.05 and mc.mean() < ev * 1.01
    sc = sample_scenarios(field, c, n=3000)
    x = np.array([scenario_cost(s, ONE, default_sizes(c, ONE)) for s in sc])
    assert abs(x.mean() / ev - 1) < 0.05
