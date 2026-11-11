"""Daisy chain: a satellite manifold ties into a hub manifold instead of running its own tie-back."""
import itertools
import math

import pytest

from layout_rel.config import param
from layout_rel.economics import capex_breakdown, hub_load, npv_breakdown, smallest_size
from layout_rel.optimizer import optimize_capex, optimize_npv
from layout_rel.reliability import failure_modes

SPLIT = {"W1": "M1", "W2": "M1", "W3": "M1", "W4": "M3", "W5": "M3", "W6": "M3"}


def link_maps(open_sites):
    """Every valid daisy-chain choice: each site goes to the host or to a hub that goes to the host."""
    sites = sorted(open_sites)
    for targets in itertools.product([None] + sites, repeat=len(sites)):
        links = {s: t for s, t in zip(sites, targets) if t is not None}
        if all(s != t and t not in links for s, t in links.items()):
            yield links


def brute_force(field, cfg, objective):
    biggest = max(param(cfg, "manifold.sizes"))
    best = None
    for combo in itertools.product(field.sites, repeat=len(field.wells)):
        a = dict(zip(field.wells, combo))
        for links in link_maps(set(combo)):
            load = hub_load(a, links)
            if max(load.values()) > biggest:
                continue
            sizes = {s: smallest_size(cfg, n) for s, n in load.items()}
            v = objective(a, sizes, links)
            if best is None or v > best[0]:
                best = (v, a, sizes, links)
    return best


@pytest.fixture
def daisy(cfg):
    cfg["routing"]["daisy_chain"]["value"] = True
    return cfg


def test_hub_failures_stop_the_satellite(field, cfg):
    modes = {m.name: m for m in failure_modes(field, cfg, SPLIT, links={"M3": "M1"})}
    assert set(modes["manifold M1"].wells) == set(field.wells)            # hub manifold: every well
    assert set(modes["tieback flowline M1"].wells) == set(field.wells)    # hub tie-back: every well
    assert set(modes["manifold M3"].wells) == {"W4", "W5", "W6"}          # satellite manifold: its wells
    assert set(modes["link flowline M3-M1"].wells) == {"W4", "W5", "W6"}
    assert "tieback flowline M3" not in modes                             # no own tie-back


def test_link_replaces_the_satellite_tieback_in_capex(field, cfg):
    own = capex_breakdown(field, cfg, SPLIT)
    chained = capex_breakdown(field, cfg, SPLIT, links={"M3": "M1"})
    assert chained["link_lines"] > 0 and chained["tieback_lines"] < own["tieback_lines"]
    assert hub_load(SPLIT, {"M3": "M1"}) == {"M1": 4, "M3": 3}            # incoming line takes a slot
    with pytest.raises(ValueError):
        capex_breakdown(field, cfg, SPLIT, links={"M3": "M1", "M1": "M3"})  # a hub cannot be a satellite


def test_daisy_off_gives_the_old_model(field, cfg):
    assert param(cfg, "routing.daisy_chain") is False
    assert optimize_npv(field, cfg).links == {}


def test_capex_milp_with_daisy_chain_matches_brute_force(field, daisy):
    sol = optimize_capex(field, daisy)
    best = brute_force(field, daisy, lambda a, s, l: -capex_breakdown(field, daisy, a, s, l)["total"])
    assert math.isclose(sol.objective, -best[0], rel_tol=1e-6)
    assert math.isclose(sol.objective, capex_breakdown(field, daisy, sol.assignment, sol.sizes, sol.links)["total"], rel_tol=1e-6)


def test_npv_milp_with_daisy_chain_matches_brute_force(field, daisy):
    sol = optimize_npv(field, daisy)
    best = brute_force(field, daisy, lambda a, s, l: npv_breakdown(field, daisy, a, s, l)["npv"])
    assert math.isclose(sol.objective, best[0], rel_tol=1e-9)
    assert math.isclose(sol.objective, npv_breakdown(field, daisy, sol.assignment, sol.sizes, sol.links)["npv"], rel_tol=1e-9)


def test_npv_milp_matches_brute_force_when_chaining_pays(field, daisy):
    """Costly failures and a long tie-back: the optimum should split and chain."""
    for k in ("msv_mobilisation", "hlv_mobilisation"):
        daisy["vessels"][k]["value"] *= 3
    daisy["reliability"]["manifold"]["failure_rate_per_h"]["value"] *= 3
    sol = optimize_npv(field, daisy)
    best = brute_force(field, daisy, lambda a, s, l: npv_breakdown(field, daisy, a, s, l)["npv"])
    assert math.isclose(sol.objective, best[0], rel_tol=1e-9)
    assert len(sol.sizes) >= 2


def test_risk_averse_milp_refuses_daisy_chain(field, daisy):
    with pytest.raises(NotImplementedError):
        optimize_npv(field, daisy, risk_weight=0.5)


def test_milp_prices_a_fixed_chained_layout_like_the_npv_model(field, daisy):
    """Fix a chained layout in the MILP: its cost must equal the direct NPV calculation."""
    import pyomo.environ as pyo

    from layout_rel.optimizer import build_npv_model, solve
    for stops in (True, False):
        daisy["routing"]["hub_manifold_stops_satellites"]["value"] = stops
        links, sizes = {"M3": "M1"}, {"M1": 4, "M3": 4}
        m = build_npv_model(field, daisy, risk_weight=0.0)
        for w, s in SPLIT.items():
            for t in field.sites:
                m.assign[w, t].fix(1 if t == s else 0)
        for s in field.sites:
            for k in m.K:
                m.size[s, k].fix(1 if sizes.get(s) == k else 0)
            m.tb[s].fix(1 if s in sizes and s not in links else 0)
        for (s, t) in m.P:
            m.lnk[s, t].fix(1 if links.get(s) == t else 0)
        sol = solve(m, daisy)
        assert sol.links == links
        assert math.isclose(m.revenue_pv - sol.objective, npv_breakdown(field, daisy, SPLIT, sizes, links)["npv"], rel_tol=1e-9)


def test_bypass_option_frees_satellites_from_hub_manifold_failures(field, cfg):
    cfg["routing"]["hub_manifold_stops_satellites"]["value"] = False
    modes = {m.name: m for m in failure_modes(field, cfg, SPLIT, links={"M3": "M1"})}
    assert set(modes["manifold M1"].wells) == {"W1", "W2", "W3"}
    assert set(modes["tieback flowline M1"].wells) == set(field.wells)     # shared tie-back still stops all
