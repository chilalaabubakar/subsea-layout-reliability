"""Pyomo MILP for choosing manifold sites, manifold sizes and well connections.

Case 1: minimise CAPEX.
Case 2: maximise NPV = PV(revenue) - CAPEX - PV(OPEX) - PV(expected failure cost).
        PV(revenue) is the same for every layout, so this is solved as
        minimise CAPEX * (1 + opex_fraction * A_rep) + PV(failure cost).

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

Case 2 adds z[w,s,k] >= assign[w,s] + size[s,k] - 1 (z >= 0), the linear form of
assign*size, needed because a manifold's failure rate depends on its slot count
and its failure stops every well on it. z has a positive cost and is minimised,
so it equals the product at the optimum.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import pyomo.environ as pyo

from .config import param
from .economics import annuity_factors, capex_coefficients, manifold_sizes, revenue_pv
from .maintenance import failure_cost_coefficients
from .layout import Field


@dataclass
class LayoutSolution:
    open_sites: list[str]
    assignment: dict[str, str]          # {well: site}
    sizes: dict[str, int]               # {site: slots}
    objective: float                    # USD
    status: str
    info: dict = dc_field(default_factory=dict)


def _base_model(field: Field, cfg: dict, name: str) -> pyo.ConcreteModel:
    """Sets, variables and layout constraints shared by case 1 and case 2."""
    m = pyo.ConcreteModel(name=name)
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

    c = capex_coefficients(field, cfg)
    m.capex_expr = pyo.Expression(expr=c.tree_total
        + sum(c.manifold[k] * m.size[s, k] for s in m.S for k in m.K)
        + sum(c.tieback[s] * m.open[s] for s in m.S)
        + sum(c.connect[w, s] * m.assign[w, s] for w in m.W for s in m.S))
    return m


def build_capex_model(field: Field, cfg: dict) -> pyo.ConcreteModel:
    """Case 1: minimise CAPEX."""
    m = _base_model(field, cfg, "capex_only")
    m.cost = pyo.Objective(expr=m.capex_expr, sense=pyo.minimize)
    return m


def build_npv_model(field: Field, cfg: dict) -> pyo.ConcreteModel:
    """Case 2: maximise NPV including expected failure cost (solved as min of costs)."""
    m = _base_model(field, cfg, "npv_with_failures")
    a_rep, a_prod = annuity_factors(cfg)
    f = failure_cost_coefficients(field, cfg, repair_weight=a_rep, production_weight=a_prod)

    m.z = pyo.Var(m.W, m.S, m.K, domain=pyo.NonNegativeReals)
    m.z_link = pyo.Constraint(m.W, m.S, m.K, rule=lambda m, w, s, k:
                              m.z[w, s, k] >= m.assign[w, s] + m.size[s, k] - 1)

    m.failure_expr = pyo.Expression(expr=f.constant
        + sum(f.site[s] * m.open[s] for s in m.S)
        + sum(f.site_size[s, k] * m.size[s, k] for s in m.S for k in m.K)
        + sum(f.connect[w, s] * m.assign[w, s] for w in m.W for s in m.S)
        + sum(f.connect_size[w, s, k] * m.z[w, s, k] for w in m.W for s in m.S for k in m.K))
    opex_factor = param(cfg, "economics.opex_fraction_of_capex") * a_rep
    m.cost = pyo.Objective(expr=m.capex_expr * (1 + opex_factor) + m.failure_expr,
                           sense=pyo.minimize)
    m.revenue_pv = revenue_pv(field, cfg)
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
                          objective=pyo.value(m.cost), status=status)


def optimize_capex(field: Field, cfg: dict) -> LayoutSolution:
    """Case 1: CAPEX-only optimal layout. ``objective`` = CAPEX [USD]."""
    return solve(build_capex_model(field, cfg), cfg)


def optimize_npv(field: Field, cfg: dict) -> LayoutSolution:
    """Case 2: NPV-optimal layout incl. failures. ``objective`` = NPV [USD]."""
    m = build_npv_model(field, cfg)
    sol = solve(m, cfg)
    sol.info["cost_pv"] = sol.objective
    sol.objective = m.revenue_pv - sol.objective
    return sol
