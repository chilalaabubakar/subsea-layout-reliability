"""Failure modes of a layout: which component fails, how often, and which wells stop.

Constant failure rates (exponential model, MTTF = 1/lambda). For a given layout
({well: site}), every component becomes one ``FailureMode``:

    X-mas tree (incl. SCM)        one per well       stops that well
    infield flowline              one per well       stops that well        rate per km x length
    infield umbilical             one per well       stops that well        rate per unit
    manifold                      one per open site  stops all its wells
    tie-back flowline             one per open site  stops all its wells    rate per km x length
    tie-back umbilical            one per open site  stops all its wells    rate per unit
                                                                         (not scaled by length)

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
    """Rate [1/s] of failures of a ``slots``-slot manifold that stop production.

    ``critical_fraction`` is the share of the recorded failures that stop production and
    need an immediate repair (1 in the base case); the others are taken to be repaired in
    planned campaigns and are not counted.
    """
    ref = param(cfg, "reliability.manifold.failure_rate_per_h")
    f = param(cfg, "reliability.manifold.slot_fraction")
    k_ref = param(cfg, "reliability.manifold.reference_slots")
    return ref * param(cfg, "reliability.manifold.critical_fraction") * ((1 - f) + f * slots / k_ref)


def rate(cfg: dict, component: str, length: float | None = None, slots: int | None = None) -> float:
    """Failure rate [1/s] of one component; ``length`` [m] for lines, ``slots`` for manifolds.

    A line given ``failure_rate_per_km`` in the config scales with its route length; one
    given ``failure_rate_per_unit`` (the umbilicals: OREDA reports umbilical failures per
    installed unit, not per km) has the same rate whatever its length. Callers pass the
    length of every line, so either form can be set in the config.
    """
    if component == "manifold":
        if slots is None:
            raise ValueError("manifold rate needs the slot count")
        return manifold_rate(cfg, slots)
    node = cfg["reliability"][component]
    if "failure_rate_per_km" in node:
        if length is None:
            raise ValueError(f"{component} has a per-km failure rate and needs the route length")
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
                    rate(cfg, "infield_umbilical", L), (well,)),
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
                    rate(cfg, "tieback_umbilical", L), wells),
    ]


def link_modes(field: Field, cfg: dict, sat: str, hub: str, wells: tuple[str, ...]) -> list[FailureMode]:
    """Failure modes of the daisy-chain lines from satellite ``sat`` to hub ``hub``.

    They carry only the satellite's wells, so a failure stops those wells. They fail and
    are repaired like tie-back lines of the same length.
    """
    L = field.length(sat, hub)
    return [
        FailureMode(f"link flowline {sat}-{hub}", REPAIR_KIND["tieback_flowline"],
                    rate(cfg, "tieback_flowline", L), wells),
        FailureMode(f"link umbilical {sat}-{hub}", REPAIR_KIND["tieback_umbilical"],
                    rate(cfg, "tieback_umbilical", L), wells),
    ]


def failure_modes(field: Field, cfg: dict, assignment: dict[str, str],
                  sizes: dict[str, int] | None = None,
                  links: dict[str, str] | None = None) -> list[FailureMode]:
    """All failure modes of a layout given as {well: site} and {site: slots}.

    If ``sizes`` is omitted, each site gets the smallest manifold that fits its wells (and
    one slot per satellite tied into it). ``links`` maps a satellite site to its hub site
    (daisy chain): the satellite has no tie-back of its own, and a failure of the hub's
    manifold or tie-back also stops the satellite's wells.
    """
    from .economics import check_links, hub_load, smallest_size     # local import avoids a cycle
    links = links or {}
    check_links(assignment, links)
    load = hub_load(assignment, links)
    modes: list[FailureMode] = []
    for w in field.wells:
        modes += well_modes(field, cfg, w, assignment[w])
    own = {s: tuple(w for w in field.wells if assignment[w] == s) for s in set(assignment.values())}
    for s in sorted(own):
        k = sizes[s] if sizes else smallest_size(cfg, load[s])
        if s in links:                                   # satellite: own manifold, link lines
            modes.append(site_modes(field, cfg, s, own[s], k)[0])
            modes += link_modes(field, cfg, s, links[s], own[s])
        else:                                            # hub or stand-alone: wells behind it too
            behind = own[s] + tuple(w for sat, hub in links.items() if hub == s for w in own[sat])
            man, *tie = site_modes(field, cfg, s, behind, k)
            if not param(cfg, "routing.hub_manifold_stops_satellites"):
                man = FailureMode(man.name, man.repair_kind, man.rate, own[s])
            modes += [man, *tie]
    return modes
