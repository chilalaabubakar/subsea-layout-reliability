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
