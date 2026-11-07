"""Check the MILP against brute force: try every feasible assignment."""
import itertools
import math

from layout_rel.config import param
from layout_rel.economics import capex_breakdown
from layout_rel.optimizer import optimize_capex


def brute_force_min(field, cfg):
    biggest = max(param(cfg, "manifold.sizes"))
    best = math.inf
    for combo in itertools.product(field.sites, repeat=len(field.wells)):
        if any(combo.count(s) > biggest for s in field.sites):
            continue
        # each open site gets its cheapest feasible size (capex_breakdown default)
        best = min(best, capex_breakdown(field, cfg, dict(zip(field.wells, combo)))["total"])
    return best


def check(field, cfg):
    sol = optimize_capex(field, cfg)
    assert set(sol.assignment) == set(field.wells)
    assert math.isclose(sol.objective, brute_force_min(field, cfg), rel_tol=1e-6)
    assert math.isclose(
        sol.objective,
        capex_breakdown(field, cfg, sol.assignment, sol.sizes)["total"], rel_tol=1e-9)
    for s in sol.open_sites:
        assert list(sol.assignment.values()).count(s) <= sol.sizes[s]
    return sol


def test_capex_milp_is_optimal(field, cfg):
    check(field, cfg)


def test_fixed_4_slot_manifolds(field, cfg):
    cfg["manifold"]["sizes"]["value"] = [4]        # 6 wells need >= 2 manifolds
    sol = check(field, cfg)
    assert len(sol.open_sites) >= 2


def test_2_slot_manifolds_force_three(field, cfg):
    cfg["manifold"]["sizes"]["value"] = [2]
    sol = check(field, cfg)
    assert len(sol.open_sites) == 3
