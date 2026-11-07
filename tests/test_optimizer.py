"""Check the MILP against brute force: try every feasible assignment."""
import itertools
import math

from layout_rel.config import param
from layout_rel.economics import capex_breakdown
from layout_rel.optimizer import optimize_capex


def brute_force_min(field, cfg):
    slots = param(cfg, "manifold.slots")
    best = math.inf
    for combo in itertools.product(field.sites, repeat=len(field.wells)):
        if any(combo.count(s) > slots for s in field.sites):
            continue
        best = min(best, capex_breakdown(field, cfg, dict(zip(field.wells, combo)))["total"])
    return best


def test_capex_milp_is_optimal(field, cfg):
    sol = optimize_capex(field, cfg)
    assert set(sol.assignment) == set(field.wells)
    assert math.isclose(sol.objective, brute_force_min(field, cfg), rel_tol=1e-6)
    assert math.isclose(sol.objective,
                        capex_breakdown(field, cfg, sol.assignment)["total"], rel_tol=1e-9)


def test_capacity_respected(field, cfg):
    cfg["manifold"]["slots"]["value"] = 2      # force 3 manifolds
    sol = optimize_capex(field, cfg)
    assert len(sol.open_sites) == 3
    for s in sol.open_sites:
        assert list(sol.assignment.values()).count(s) <= 2
    assert math.isclose(sol.objective, brute_force_min(field, cfg), rel_tol=1e-6)
