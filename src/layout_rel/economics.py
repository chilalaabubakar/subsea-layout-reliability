"""Cost model: CAPEX, OPEX and field-life NPV.

CAPEX of a layout =
    trees      : n_wells * installed tree cost
  + manifolds  : sum over open sites of installed manifold cost (depends on slot size)
  + infield    : sum over wells of length(well, its manifold)
                 * (infield flowline + infield umbilical cost per m)
  + tie-back   : sum over open sites of length(site, host)
                 * (tie-back flowline + tie-back umbilical cost per m)

Installed unit cost (Bai & Bai 2010, Ch. 6) = procurement + SIT testing
    + installation days * vessel day rate (+ foundation for manifolds).

The same per-element costs feed the MILP (``capex_coefficients``) and the
independent check of a given layout (``capex_breakdown``), so the two can
never disagree.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import param, param_raw
from .layout import Field


def _day_rate(cfg: dict, item: str) -> float:
    vessel = param(cfg, f"capex.{item}.install_vessel")
    return param(cfg, f"vessels.{vessel}_day_rate")


def tree_cost(cfg: dict) -> float:
    """Installed cost of one X-mas tree [USD]."""
    return (param(cfg, "capex.xmas_tree.procurement")
            + param(cfg, "capex.xmas_tree.sit")
            + param(cfg, "capex.xmas_tree.install_days") * _day_rate(cfg, "xmas_tree"))


def manifold_cost(cfg: dict, slots: int) -> float:
    """Installed cost of one cluster manifold with ``slots`` slots [USD]."""
    factor = param(cfg, "manifold.slot_cost_factor")[slots]
    return (factor * param(cfg, "capex.manifold.procurement_base")
            + param(cfg, "capex.manifold.procurement_misc")
            + param(cfg, "capex.manifold.sit")
            + param(cfg, "capex.manifold.foundation")
            + param(cfg, "capex.manifold.install_days") * _day_rate(cfg, "manifold"))


def manifold_sizes(cfg: dict) -> list[int]:
    return sorted(param(cfg, "manifold.sizes"))


def smallest_size(cfg: dict, n_wells: int) -> int:
    """Smallest available manifold that takes ``n_wells`` wells."""
    for k in manifold_sizes(cfg):
        if k >= n_wells:
            return k
    raise ValueError(f"No manifold size holds {n_wells} wells")


def _per_m(cfg: dict, kind: str) -> float:
    return param(cfg, f"capex.{kind}_flowline") + param(cfg, f"capex.{kind}_umbilical")


@dataclass
class CapexCoefficients:
    tree_total: float                        # USD, same for every layout
    manifold: dict[int, float]               # USD for a manifold with k slots
    tieback: dict[str, float]                # USD if site s is opened (lines to host)
    connect: dict[tuple[str, str], float]    # USD to connect well w to site s


def capex_coefficients(field: Field, cfg: dict) -> CapexCoefficients:
    tieback_per_m, infield_per_m = _per_m(cfg, "tieback"), _per_m(cfg, "infield")
    return CapexCoefficients(
        tree_total=tree_cost(cfg) * len(field.wells),
        manifold={k: manifold_cost(cfg, k) for k in manifold_sizes(cfg)},
        tieback={s: tieback_per_m * field.length(s, field.host) for s in field.sites},
        connect={(w, s): infield_per_m * field.length(w, s)
                 for w in field.wells for s in field.sites},
    )


def capex_breakdown(field: Field, cfg: dict, assignment: dict[str, str],
                    sizes: dict[str, int] | None = None) -> dict[str, float]:
    """CAPEX [USD] by category for a layout given as {well: site}.

    ``sizes`` gives the slot size per open site; if omitted, each site gets the
    smallest manifold that fits its wells (the cheapest choice).
    """
    missing = set(field.wells) - set(assignment)
    if missing:
        raise ValueError(f"Wells not assigned: {sorted(missing)}")
    c = capex_coefficients(field, cfg)
    count = {s: list(assignment.values()).count(s) for s in set(assignment.values())}
    if sizes is None:
        sizes = {s: smallest_size(cfg, n) for s, n in count.items()}
    for s, n in count.items():
        if sizes[s] < n:
            raise ValueError(f"{s}: {n} wells on a {sizes[s]}-slot manifold")

    out = {
        "trees": c.tree_total,
        "manifolds": sum(c.manifold[sizes[s]] for s in count),
        "infield_lines": sum(c.connect[w, s] for w, s in assignment.items()),
        "tieback_lines": sum(c.tieback[s] for s in count),
    }
    out["total"] = sum(out.values())
    return out


# ---------------------------------------------------------------- NPV (step 6)
#
# CAPEX is spent at t = 0; production years are t = 1..N (N = field_life).
# Plateau rate for `plateau_years`, then exponential decline. Cash flows are
# discounted with (1 + r)^-t at the end of each year.
#
#   NPV = PV(revenue) - CAPEX - PV(OPEX) - PV(expected failure cost)
#   PV(failure cost) = repair cost/yr * A_rep + lost production/yr (at plateau) * A_prod
#   A_rep  = sum_t DF_t            (failures happen at a constant rate)
#   A_prod = sum_t DF_t * g_t      (g_t = production at t / plateau; loss scales with rate)
#
# Base case: lost production is lost, not deferred (conservative). With
# `production.deferred_fraction` > 0 that share of the shut-in volume is produced later
# and credited at the discount factor of its recovery year (`lost_production_weights`).

def production_profile(cfg: dict) -> list[float]:
    """g_t = production in year t relative to plateau, t = 1..N."""
    from .units import YEAR
    n = round(param(cfg, "economics.field_life") / YEAR)
    plateau = param(cfg, "economics.plateau_years") / YEAR
    d = param(cfg, "economics.decline_rate")
    return [1.0 if t <= plateau else (1 - d) ** (t - plateau) for t in range(1, n + 1)]


def discount_factors(cfg: dict) -> list[float]:
    r = param(cfg, "economics.discount_rate")
    return [(1 + r) ** -t for t in range(1, len(production_profile(cfg)) + 1)]


def lost_production_weights(cfg: dict) -> list[float]:
    """Present-value weight of production lost in year t (t = 1..N).

    Without deferral this is the discount factor DF_t. If a share ``delta``
    (``production.deferred_fraction``) of the shut-in volume is produced later, it is
    credited at the discount factor of its recovery: the last year of field life
    (``production.deferral_delay`` null, the deferred volume extends the tail of the decline)
    or ``deferral_delay`` years after the outage. Weight = DF_t - delta * DF_recovery.
    """
    df = discount_factors(cfg)
    delta = param(cfg, "production.deferred_fraction")
    if not delta:
        return df
    delay = param_raw(cfg, "production.deferral_delay")          # years, or None
    r = param(cfg, "economics.discount_rate")
    recovery = [df[-1]] * len(df) if delay is None else [f * (1 + r) ** -delay for f in df]
    return [f - delta * c for f, c in zip(df, recovery)]


def annuity_factors(cfg: dict) -> tuple[float, float]:
    """(A_rep, A_prod) for failure costs: discounted sum of years, and of production-weighted
    years. A_prod uses ``lost_production_weights``, so it includes the credit for deferred
    production (none in the base case)."""
    df, g = discount_factors(cfg), production_profile(cfg)
    return sum(df), sum(f * x for f, x in zip(lost_production_weights(cfg), g))


def revenue_pv(field: Field, cfg: dict) -> float:
    """PV of revenue with no downtime [USD] (same for every layout)."""
    from .units import YEAR
    q = sum(param(cfg, "production.well_rate") for _ in field.wells)
    a_prod = sum(f * x for f, x in zip(discount_factors(cfg), production_profile(cfg)))
    return q * YEAR * param(cfg, "production.oil_price") * a_prod


def npv_breakdown(field: Field, cfg: dict, assignment: dict[str, str],
                  sizes: dict[str, int] | None = None) -> dict[str, float]:
    """NPV and its parts [USD] for a layout."""
    from .maintenance import expected_failure_cost
    if sizes is None:
        count = {s: list(assignment.values()).count(s) for s in set(assignment.values())}
        sizes = {s: smallest_size(cfg, n) for s, n in count.items()}
    a_rep, a_prod = annuity_factors(cfg)
    capex = capex_breakdown(field, cfg, assignment, sizes)["total"]
    f = expected_failure_cost(field, cfg, assignment, sizes)
    out = {
        "revenue": revenue_pv(field, cfg),
        "capex": capex,
        "opex": param(cfg, "economics.opex_fraction_of_capex") * capex * a_rep,
        "repair_cost": f.repair_cost * a_rep,
        "lost_production": f.lost_production * a_prod,
    }
    out["npv"] = out["revenue"] - out["capex"] - out["opex"] - out["repair_cost"] - out["lost_production"]
    return out
