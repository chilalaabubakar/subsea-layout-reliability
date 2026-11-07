"""Cost model. Currently: CAPEX only (OPEX and NPV come in work plan step 6).

CAPEX of a layout =
    trees      : n_wells * tree cost
  + manifolds  : (number of open sites) * manifold cost
  + infield    : sum over wells of length(well, its manifold)
                 * (infield flowline + infield umbilical cost per m)
  + tie-back   : sum over open sites of length(site, host)
                 * (tie-back flowline + tie-back umbilical cost per m)

The same per-element costs feed the MILP (``capex_coefficients``) and the
independent check of a given layout (``capex_breakdown``), so the two can
never disagree.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import param
from .layout import Field


@dataclass
class CapexCoefficients:
    tree_total: float                    # USD, same for every layout
    site_fixed: dict[str, float]         # USD if site is opened (manifold + tie-back)
    connect: dict[tuple[str, str], float]  # USD to connect well w to site s


def capex_coefficients(field: Field, cfg: dict) -> CapexCoefficients:
    tree = param(cfg, "capex.xmas_tree")
    manifold = param(cfg, "capex.manifold")
    infield_per_m = (param(cfg, "capex.infield_flowline")
                     + param(cfg, "capex.infield_umbilical"))
    tieback_per_m = (param(cfg, "capex.tieback_flowline")
                     + param(cfg, "capex.tieback_umbilical"))

    site_fixed = {s: manifold + tieback_per_m * field.length(s, field.host)
                  for s in field.sites}
    connect = {(w, s): infield_per_m * field.length(w, s)
               for w in field.wells for s in field.sites}
    return CapexCoefficients(tree_total=tree * len(field.wells),
                             site_fixed=site_fixed, connect=connect)


def capex_breakdown(field: Field, cfg: dict,
                    assignment: dict[str, str]) -> dict[str, float]:
    """CAPEX [USD] by category for a layout given as {well: site}."""
    missing = set(field.wells) - set(assignment)
    if missing:
        raise ValueError(f"Wells not assigned: {sorted(missing)}")
    open_sites = sorted(set(assignment.values()))

    manifold = param(cfg, "capex.manifold")
    infield_per_m = (param(cfg, "capex.infield_flowline")
                     + param(cfg, "capex.infield_umbilical"))
    tieback_per_m = (param(cfg, "capex.tieback_flowline")
                     + param(cfg, "capex.tieback_umbilical"))

    out = {
        "trees": param(cfg, "capex.xmas_tree") * len(field.wells),
        "manifolds": manifold * len(open_sites),
        "infield_lines": sum(infield_per_m * field.length(w, s)
                             for w, s in assignment.items()),
        "tieback_lines": sum(tieback_per_m * field.length(s, field.host)
                             for s in open_sites),
    }
    out["total"] = sum(out.values())
    return out
