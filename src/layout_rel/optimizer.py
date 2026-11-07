"""Pyomo MILP for choosing manifold sites and well-to-manifold connections.

Case 1 (this file, for now): minimise CAPEX.

Decision variables
    open[s]      = 1 if a manifold is installed at candidate site s
    assign[w, s] = 1 if well w is tied in to the manifold at site s

Constraints
    each well connected to exactly one manifold:   sum_s assign[w,s] = 1
    slot capacity, only open sites take wells:      sum_w assign[w,s] <= slots * open[s]
    (tightening) a well can only use an open site:  assign[w,s] <= open[s]
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import pyomo.environ as pyo

from .config import param
from .economics import capex_coefficients
from .layout import Field


@dataclass
class LayoutSolution:
    open_sites: list[str]
    assignment: dict[str, str]          # {well: site}
    objective: float                    # USD
    status: str
    info: dict = dc_field(default_factory=dict)


def build_capex_model(field: Field, cfg: dict) -> pyo.ConcreteModel:
    c = capex_coefficients(field, cfg)
    slots = param(cfg, "manifold.slots")

    m = pyo.ConcreteModel(name="capex_only")
    m.W = pyo.Set(initialize=field.wells, ordered=True)
    m.S = pyo.Set(initialize=field.sites, ordered=True)

    m.open = pyo.Var(m.S, domain=pyo.Binary)
    m.assign = pyo.Var(m.W, m.S, domain=pyo.Binary)

    m.one_manifold = pyo.Constraint(
        m.W, rule=lambda m, w: sum(m.assign[w, s] for s in m.S) == 1)
    m.capacity = pyo.Constraint(
        m.S, rule=lambda m, s: sum(m.assign[w, s] for w in m.W) <= slots * m.open[s])
    m.link = pyo.Constraint(
        m.W, m.S, rule=lambda m, w, s: m.assign[w, s] <= m.open[s])

    m.capex = pyo.Objective(
        expr=c.tree_total
        + sum(c.site_fixed[s] * m.open[s] for s in m.S)
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

    open_sites = [s for s in m.S if pyo.value(m.open[s]) > 0.5]
    assignment = {w: s for w in m.W for s in m.S
                  if pyo.value(m.assign[w, s]) > 0.5}
    return LayoutSolution(open_sites=open_sites, assignment=assignment,
                          objective=pyo.value(m.capex), status=status)


def optimize_capex(field: Field, cfg: dict) -> LayoutSolution:
    """Case 1: CAPEX-only optimal layout."""
    return solve(build_capex_model(field, cfg), cfg)
