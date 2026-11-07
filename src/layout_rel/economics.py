"""Cost model. Currently: CAPEX only (OPEX and NPV come in work plan step 6).

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

from .config import param
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
