"""Failure modes of a layout: which component fails, how often, and which wells stop.

Constant failure rates (exponential model, MTTF = 1/lambda). For a given layout
({well: site}), every component becomes one ``FailureMode``:

    X-mas tree (incl. SCM)        one per well       stops that well
    infield flowline              one per well       stops that well        rate per km x length
    infield umbilical             one per well       stops that well        rate per unit
    manifold                      one per open site  stops all its wells
    tie-back flowline             one per open site  stops all its wells    rate per km x length
    tie-back umbilical            one per open site  stops all its wells    rate per unit

This is the key link between reliability and layout: grouping wells on one
manifold makes manifold and tie-back failures hit more wells at once.

The manifold rate grows with slot count k (more branch valves and couplers):
    rate(k) = rate_ref * ((1 - f) + f * k / k_ref)
Without this, the EXPECTED lost production would not depend on grouping at all
(n manifolds fail n times as often but each stops 1/n of the wells).
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import param
from .layout import Field


@dataclass(frozen=True)
class FailureMode:
    name: str                 # e.g. "manifold M2"
    repair_kind: str          # key in config `maintenance`: xmas_tree, manifold, flowline, umbilical
    rate: float               # failures per second
    wells: tuple[str, ...]    # wells that stop when it fails


def manifold_rate(cfg: dict, slots: int) -> float:
    """Failure rate [1/s] of a manifold with ``slots`` slots."""
    ref = param(cfg, "reliability.manifold.failure_rate_per_h")
    f = param(cfg, "reliability.manifold.slot_fraction")
    k_ref = param(cfg, "reliability.manifold.reference_slots")
    return ref * ((1 - f) + f * slots / k_ref)


def rate(cfg: dict, component: str, length: float = 0.0, slots: int | None = None) -> float:
    """Failure rate [1/s] of one component; ``length`` [m] for lines, ``slots`` for manifolds."""
    if component == "manifold":
        if slots is None:
            raise ValueError("manifold rate needs the slot count")
        return manifold_rate(cfg, slots)
    node = cfg["reliability"][component]
    if "failure_rate_per_km" in node:
        return param(cfg, f"reliability.{component}.failure_rate_per_km") * length
    if "failure_rate_per_unit" in node:
        return param(cfg, f"reliability.{component}.failure_rate_per_unit")
    return param(cfg, f"reliability.{component}.failure_rate_per_h")


# component -> repair kind (which `maintenance` block describes its repair)
REPAIR_KIND = {
    "xmas_tree": "xmas_tree",
    "manifold": "manifold",
    "infield_flowline": "flowline",
    "tieback_flowline": "flowline",
    "infield_umbilical": "umbilical",
    "tieback_umbilical": "umbilical",
}


def well_modes(field: Field, cfg: dict, well: str, site: str) -> list[FailureMode]:
    """Failure modes that belong to one well tied in to ``site``."""
    L = field.length(well, site)
    return [
        FailureMode(f"tree {well}", REPAIR_KIND["xmas_tree"], rate(cfg, "xmas_tree"), (well,)),
        FailureMode(f"infield flowline {well}-{site}", REPAIR_KIND["infield_flowline"],
                    rate(cfg, "infield_flowline", L), (well,)),
        FailureMode(f"infield umbilical {well}-{site}", REPAIR_KIND["infield_umbilical"],
                    rate(cfg, "infield_umbilical"), (well,)),
    ]


def site_modes(field: Field, cfg: dict, site: str, wells: tuple[str, ...],
               slots: int) -> list[FailureMode]:
    """Failure modes of an open manifold site (``slots`` slots) and its tie-back to the host."""
    L = field.length(site, field.host)
    return [
        FailureMode(f"manifold {site}", REPAIR_KIND["manifold"], rate(cfg, "manifold", slots=slots),
                    wells),
        FailureMode(f"tieback flowline {site}", REPAIR_KIND["tieback_flowline"],
                    rate(cfg, "tieback_flowline", L), wells),
        FailureMode(f"tieback umbilical {site}", REPAIR_KIND["tieback_umbilical"],
                    rate(cfg, "tieback_umbilical"), wells),
    ]


def failure_modes(field: Field, cfg: dict, assignment: dict[str, str],
                  sizes: dict[str, int] | None = None) -> list[FailureMode]:
    """All failure modes of a layout given as {well: site} and {site: slots}.

    If ``sizes`` is omitted, each site gets the smallest manifold that fits its wells.
    """
    from .economics import smallest_size          # local import avoids a cycle
    modes: list[FailureMode] = []
    for w in field.wells:
        modes += well_modes(field, cfg, w, assignment[w])
    for s in sorted(set(assignment.values())):
        wells = tuple(w for w in field.wells if assignment[w] == s)
        k = sizes[s] if sizes else smallest_size(cfg, len(wells))
        modes += site_modes(field, cfg, s, wells, k)
    return modes
