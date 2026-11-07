"""Pyomo MILP for choosing manifold sites, manifold sizes and well connections.

Case 1 (this file, for now): minimise CAPEX.

Sets: wells W, candidate sites S, manifold sizes K (slots, e.g. 2, 4, 6, 8)

Decision variables
    size[s, k]   = 1 if a k-slot manifold is installed at site s
    assign[w, s] = 1 if well w is tied in to the manifold at site s
    (open[s] = sum_k size[s, k] is an expression, not a variable)

Constraints
    at most one manifold per site:                   sum_k size[s,k] <= 1
    each well connected to exactly one manifold:     sum_s assign[w,s] = 1
    slot capacity, only open sites take wells:       sum_w assign[w,s] <= sum_k k*size[s,k]
    (tightening) a well can only use an open site:   assign[w,s] <= open[s]
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import pyomo.environ as pyo

from .config import param
from .economics import capex_coefficients, manifold_sizes
from .layout import Field


@dataclass
class LayoutSolution:
    open_sites: list[str]
    assignment: dict[str, str]          # {well: site}
    sizes: dict[str, int]               # {site: slots}
    objective: float                    # USD
    status: str
    info: dict = dc_field(default_factory=dict)


def build_capex_model(field: Field, cfg: dict) -> pyo.ConcreteModel:
    c = capex_coefficients(field, cfg)

    m = pyo.ConcreteModel(name="capex_only")
    m.W = pyo.Set(initialize=field.wells, ordered=True)
    m.S = pyo.Set(initialize=field.sites, ordered=True)
    m.K = pyo.Set(initialize=manifold_sizes(cfg), ordered=True)

    m.size = pyo.Var(m.S, m.K, domain=pyo.Binary)
    m.assign = pyo.Var(m.W, m.S, domain=pyo.Binary)
    m.open = pyo.Expression(m.S, rule=lambda m, s: sum(m.size[s, k] for k in m.K))

    m.one_size = pyo.Constraint(m.S, rule=lambda m, s: m.open[s] <= 1)
    m.one_manifold = pyo.Constraint(
        m.W, rule=lambda m, w: sum(m.assign[w, s] for s in m.S) == 1)
    m.capacity = pyo.Constraint(
        m.S, rule=lambda m, s: sum(m.assign[w, s] for w in m.W)
        <= sum(k * m.size[s, k] for k in m.K))
    m.link = pyo.Constraint(
        m.W, m.S, rule=lambda m, w, s: m.assign[w, s] <= m.open[s])

    m.capex = pyo.Objective(
        expr=c.tree_total
        + sum(c.manifold[k] * m.size[s, k] for s in m.S for k in m.K)
        + sum(c.tieback[s] * m.open[s] for s in m.S)
        + sum(c.connect[w, s] * m.assign[w, s] for w in m.W for s in m.S),
        sense=pyo.minimize)
    return m


def solve(m: pyo.ConcreteModel, cfg: dict) -> LayoutSolution:
    solver = pyo.SolverFactory(param(cfg, "solver.name"))
    solver.config.mip_gap = param(cfg, "solver.mip_gap")
    res = solver.solve(m)
    status = str(res.solver.termination_condition)
    if not pyo.check_optimal_termination(res):
        raise RuntimeError(f"Solver did not find an optimum: {status}")

    sizes = {s: k for s in m.S for k in m.K if pyo.value(m.size[s, k]) > 0.5}
    assignment = {w: s for w in m.W for s in m.S
                  if pyo.value(m.assign[w, s]) > 0.5}
    return LayoutSolution(open_sites=sorted(sizes), assignment=assignment, sizes=sizes,
                          objective=pyo.value(m.capex), status=status)


def optimize_capex(field: Field, cfg: dict) -> LayoutSolution:
    """Case 1: CAPEX-only optimal layout."""
    return solve(build_capex_model(field, cfg), cfg)
