"""Repair cost, downtime and lost production per failure; expected yearly failure cost.

Per failure of a component with repair kind k (config `maintenance.k`):
    downtime     = mobilisation(vessel) + repair_days * (1 + weather_allowance)
    repair cost  = day_rate(vessel) * downtime + spare_cost
    lost volume  = downtime * (sum of plateau rates of the wells it stops)

Expected yearly failure cost (cost model in CLAUDE.md):
    sum over failure modes of  lambda * YEAR * (repair cost + lost volume * oil price)

The vessel is assumed to be on hire from call-out until the repair is done, so
the day rate is paid over the whole downtime (mobilisation + repair + weather).
This is an expected-value model: overlapping failures and vessel queuing are
ignored; the Monte Carlo model (step 7) checks how much that matters.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import param
from .layout import Field
from .reliability import FailureMode, REPAIR_KIND, failure_modes, rate
from .units import YEAR


@dataclass(frozen=True)
class Repair:
    downtime: float       # s
    cost: float           # USD (vessel + spare)


def repair(cfg: dict, kind: str) -> Repair:
    vessel = param(cfg, f"maintenance.{kind}.vessel")
    active = param(cfg, f"maintenance.{kind}.repair_days") * (1 + param(cfg, "maintenance.weather_allowance"))
    downtime = param(cfg, f"vessels.{vessel}_mobilisation") + active
    cost = param(cfg, f"vessels.{vessel}_day_rate") * downtime + param(cfg, f"maintenance.{kind}.spare_cost")
    return Repair(downtime=downtime, cost=cost)


def well_rate(cfg: dict, well: str) -> float:
    """Plateau production rate of a well [Sm3/s] (same for all wells for now)."""
    return param(cfg, "production.well_rate")


def failures_per_year(mode: FailureMode) -> float:
    return mode.rate * YEAR


def mode_cost(cfg: dict, mode: FailureMode) -> dict[str, float]:
    """Expected yearly cost of one failure mode, split into repair and lost production."""
    r = repair(cfg, mode.repair_kind)
    n = failures_per_year(mode)
    lost_volume = n * r.downtime * sum(well_rate(cfg, w) for w in mode.wells)
    return {
        "failures": n,
        "repair_cost": n * r.cost,
        "lost_volume": lost_volume,                                   # Sm3/yr
        "lost_production": lost_volume * param(cfg, "production.oil_price"),
    }


@dataclass
class FailureCostSummary:
    repair_cost: float                 # USD/yr
    lost_production: float             # USD/yr
    lost_volume: float                 # Sm3/yr
    failures: float                    # failures/yr
    downtime_per_well: dict[str, float]  # s/yr each well is down
    by_kind: dict[str, dict[str, float]]

    @property
    def total(self) -> float:
        return self.repair_cost + self.lost_production


def expected_failure_cost(field: Field, cfg: dict, assignment: dict[str, str],
                          sizes: dict[str, int] | None = None) -> FailureCostSummary:
    """Expected yearly failure cost of a layout (plateau production, undiscounted)."""
    keys = ("failures", "repair_cost", "lost_volume", "lost_production")
    total = dict.fromkeys(keys, 0.0)
    by_kind: dict[str, dict[str, float]] = {}
    down = dict.fromkeys(field.wells, 0.0)
    for mode in failure_modes(field, cfg, assignment, sizes):
        c = mode_cost(cfg, mode)
        label = mode.name.split()[0] if not mode.name.startswith(("infield", "tieback")) \
            else " ".join(mode.name.split()[:2])
        agg = by_kind.setdefault(label, dict.fromkeys(keys, 0.0))
        for k in keys:
            total[k] += c[k]
            agg[k] += c[k]
        for w in mode.wells:
            down[w] += c["failures"] * repair(cfg, mode.repair_kind).downtime
    return FailureCostSummary(repair_cost=total["repair_cost"], lost_production=total["lost_production"],
                              lost_volume=total["lost_volume"], failures=total["failures"],
                              downtime_per_well=down, by_kind=by_kind)


@dataclass
class FailureCostCoefficients:
    """Linear form of the failure cost, for the MILP.

    cost = constant
         + sum_s      open[s]        * site[s]            (tie-back repair)
         + sum_{s,k}  size[s,k]      * site_size[s,k]     (manifold repair, depends on slots)
         + sum_{w,s}  assign[w,s]    * connect[w,s]       (well's infield lines + its tie-back loss)
         + sum_{w,s,k} z[w,s,k]      * connect_size[w,s,k] (well's loss when its k-slot manifold fails)

    with z[w,s,k] = assign[w,s] * size[s,k] (linearised in the optimizer).
    Each repair term is multiplied by ``repair_weight`` and each lost-production
    term by ``production_weight`` (1 and 1 = one plateau year, undiscounted;
    the NPV model passes discounted sums over field life).
    """
    constant: float
    site: dict[str, float]
    site_size: dict[tuple[str, int], float]
    connect: dict[tuple[str, str], float]
    connect_size: dict[tuple[str, str, int], float]


def failure_cost_coefficients(field: Field, cfg: dict, repair_weight: float = 1.0,
                              production_weight: float = 1.0) -> FailureCostCoefficients:
    from .economics import manifold_sizes
    price = param(cfg, "production.oil_price")
    wr, wp = repair_weight * YEAR, production_weight * YEAR     # rate [1/s] -> per weighted year

    def cost(comp: str, wells_rate: float, **kw) -> tuple[float, float]:
        r, lam = repair(cfg, REPAIR_KIND[comp]), rate(cfg, comp, **kw)
        return lam * wr * r.cost, lam * wp * r.downtime * wells_rate * price

    constant = sum(sum(cost("xmas_tree", well_rate(cfg, w))) for w in field.wells)
    site, site_size, connect, connect_size = {}, {}, {}, {}
    for s in field.sites:
        L = field.length(s, field.host)
        site[s] = (cost("tieback_flowline", 0.0, length=L)[0]
                   + cost("tieback_umbilical", 0.0)[0])
        for k in manifold_sizes(cfg):
            site_size[s, k] = cost("manifold", 0.0, slots=k)[0]
    for w in field.wells:
        q = well_rate(cfg, w)
        for s in field.sites:
            Lw, Ls = field.length(w, s), field.length(s, field.host)
            connect[w, s] = (sum(cost("infield_flowline", q, length=Lw))
                             + sum(cost("infield_umbilical", q))
                             + cost("tieback_flowline", q, length=Ls)[1]
                             + cost("tieback_umbilical", q)[1])
            for k in manifold_sizes(cfg):
                connect_size[w, s, k] = cost("manifold", q, slots=k)[1]
    return FailureCostCoefficients(constant, site, site_size, connect, connect_size)
