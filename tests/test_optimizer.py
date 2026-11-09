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


# ---------------------------------------------------------------- case 2 (NPV)
from layout_rel.economics import npv_breakdown          # noqa: E402
from layout_rel.optimizer import optimize_npv            # noqa: E402


def brute_force_max_npv(field, cfg):
    biggest = max(param(cfg, "manifold.sizes"))
    best = -math.inf
    for combo in itertools.product(field.sites, repeat=len(field.wells)):
        if any(combo.count(s) > biggest for s in field.sites):
            continue
        # smallest feasible size is best: CAPEX and failure rate both grow with slots
        best = max(best, npv_breakdown(field, cfg, dict(zip(field.wells, combo)))["npv"])
    return best


def check_npv(field, cfg):
    sol = optimize_npv(field, cfg)
    assert math.isclose(sol.objective, brute_force_max_npv(field, cfg), rel_tol=1e-9)
    assert math.isclose(sol.objective,
                        npv_breakdown(field, cfg, sol.assignment, sol.sizes)["npv"], rel_tol=1e-9)
    return sol


def test_npv_milp_is_optimal(field, cfg):
    check_npv(field, cfg)


def test_unreliable_manifolds_split_the_field(field, cfg):
    # with very frequent manifold failures and slow vessels, grouping must be punished
    cfg["reliability"]["manifold"]["failure_rate_per_h"]["value"] *= 10
    cfg["vessels"]["hlv_mobilisation"]["value"] = 90.0
    sol = check_npv(field, cfg)
    assert len(sol.open_sites) >= 2


# ---------------------------------------------------------------- Solveig (4 sites: 4^6 = 4,096 assignments)
def _solveig():
    from layout_rel.config import REPO_ROOT, field_path, load_config
    from layout_rel.layout import load_field
    cfg = load_config(REPO_ROOT / "config" / "solveig_weather.yaml")
    return load_field(field_path(cfg), param(cfg, "routing.length_factor")), cfg


def test_solveig_milps_match_brute_force():
    """Cases 1 and 2 of the North Sea case return the optimum of full enumeration."""
    field, cfg = _solveig()
    assert len(field.sites) ** len(field.wells) == 4096
    check(field, cfg)
    check_npv(field, cfg)
