"""Monte Carlo simulation of random failures over field life.

Two uses:

1. ``simulate_layout``: the "truth" check of the expected-value (EV) model for one
   fixed layout. Failures arrive as Poisson processes (constant rates, as in the EV
   model). Each failure takes its wells down for [t, t + downtime]. Overlapping
   outages of the same well are merged, so lost production is not counted twice,
   and outages are cut at the end of field life. The EV model ignores both effects.

2. ``sample_scenarios``: failure scenarios for the risk-averse (CVaR) MILP. Each
   scenario is written in the same linear form as the EV coefficients
   (``maintenance.FailureCostCoefficients``), so the MILP can use it directly. Here
   overlaps are ignored (as in the EV model) to keep the cost linear in the layout.

Both use the EV model's money conventions: a failure in year y (t in (y-1, y]) is
discounted with (1 + r)^-y and its lost production uses the production level g_y,
so the MC mean and the EV value differ only by overlap and end-of-life effects
plus sampling noise. Vessel queuing (two repairs waiting for one vessel) is not
modelled in either.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .config import param
from .economics import discount_factors, manifold_sizes, production_profile, smallest_size
from .layout import Field
from .maintenance import FailureCostCoefficients, repair, well_rate
from .reliability import REPAIR_KIND, failure_modes, rate
from .units import YEAR


@dataclass
class SimulationResult:
    repair_pv: np.ndarray          # USD per simulated field life
    lost_pv: np.ndarray            # USD
    downtime: np.ndarray           # s of well-downtime per field life, summed over wells
    failures: np.ndarray           # number of failures per field life

    @property
    def total_pv(self) -> np.ndarray:
        return self.repair_pv + self.lost_pv


def cvar(x: np.ndarray, alpha: float) -> float:
    """Mean of the worst (1 - alpha) share of outcomes (costs: high is bad)."""
    x = np.sort(np.asarray(x))
    k = int(math.ceil(alpha * len(x)))
    return float(x[k:].mean()) if k < len(x) else float(x[-1])


def summary(x: np.ndarray, alpha: float) -> dict[str, float]:
    x = np.asarray(x)
    return {"mean": float(x.mean()), "std": float(x.std(ddof=1)),
            "se_mean": float(x.std(ddof=1) / math.sqrt(len(x))),
            "p50": float(np.percentile(x, 50)), "p90": float(np.percentile(x, 90)),
            f"cvar{int(alpha * 100)}": cvar(x, alpha), "max": float(x.max())}


def _year_tables(cfg: dict) -> tuple[np.ndarray, np.ndarray, float]:
    df = np.array(discount_factors(cfg))
    g = np.array(production_profile(cfg))
    return df, g, len(df) * YEAR


def _lost_pv_of_intervals(intervals: list[tuple[float, float]], q: float, price: float,
                          df: np.ndarray, g: np.ndarray, life: float) -> tuple[float, float]:
    """Merge outage intervals of one well; return (PV of lost production, total downtime)."""
    if not intervals:
        return 0.0, 0.0
    intervals.sort()
    merged = [list(intervals[0])]
    for a, b in intervals[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    pv = down = 0.0
    for a, b in merged:
        b = min(b, life)
        down += b - a
        y0, y1 = int(a // YEAR), int(min(math.ceil(b / YEAR), len(df)))
        for y in range(y0, y1):                      # year index y -> year y + 1
            overlap = min(b, (y + 1) * YEAR) - max(a, y * YEAR)
            if overlap > 0:
                pv += overlap * q * g[y] * price * df[y]
    return pv, down


def simulate_layout(field: Field, cfg: dict, assignment: dict[str, str],
                    sizes: dict[str, int] | None = None, n: int | None = None,
                    seed: int | None = None) -> SimulationResult:
    """Simulate ``n`` field lives of a fixed layout (with outage overlap)."""
    n = int(n or param(cfg, "montecarlo.n_sims"))
    rng = np.random.default_rng(param(cfg, "montecarlo.seed") if seed is None else seed)
    df, g, life = _year_tables(cfg)
    price = param(cfg, "production.oil_price")
    modes = [m for m in failure_modes(field, cfg, assignment, sizes) if m.rate > 0]
    reps = [repair(cfg, m.repair_kind) for m in modes]
    q = {w: well_rate(cfg, w) for w in field.wells}

    repair_pv, lost_pv = np.zeros(n), np.zeros(n)
    downtime, failures = np.zeros(n), np.zeros(n)
    counts = rng.poisson([m.rate * life for m in modes], size=(n, len(modes)))
    for i in range(n):
        outages: dict[str, list[tuple[float, float]]] = {w: [] for w in field.wells}
        for j in np.nonzero(counts[i])[0]:
            m, r = modes[j], reps[j]
            times = rng.uniform(0.0, life, counts[i, j])     # Poisson: uniform given count
            years = np.minimum((times // YEAR).astype(int), len(df) - 1)
            repair_pv[i] += r.cost * df[years].sum()
            failures[i] += len(times)
            for t in times:
                for w in m.wells:
                    outages[w].append((t, t + r.downtime))
        for w, iv in outages.items():
            pv, d = _lost_pv_of_intervals(iv, q[w], price, df, g, life)
            lost_pv[i] += pv
            downtime[i] += d
    return SimulationResult(repair_pv, lost_pv, downtime, failures)


# ------------------------------------------------------------ scenarios for CVaR MILP

def sample_scenarios(field: Field, cfg: dict, n: int | None = None,
                     seed: int | None = None) -> list[FailureCostCoefficients]:
    """Sampled failure scenarios, each in the linear MILP form (PV over field life).

    For every candidate component (tree per well, line per well-site pair, manifold per
    site and size, tie-back per site) failure times are drawn once per scenario. All
    wells tied to a site see the SAME manifold/tie-back events (common cause). Manifold
    sizes share one event stream, thinned by rate(k)/rate(k_max), so a bigger manifold
    always fails at least as often as a smaller one in the same scenario.
    """
    n = int(n or param(cfg, "risk.n_scenarios"))
    rng = np.random.default_rng(param(cfg, "risk.seed") if seed is None else seed)
    df, g, life = _year_tables(cfg)
    price = param(cfg, "production.oil_price")
    sizes = manifold_sizes(cfg)

    def events(lam: float) -> np.ndarray:
        """Year indices of failures in one field life."""
        t = rng.uniform(0.0, life, rng.poisson(lam * life))
        return np.minimum((t // YEAR).astype(int), len(df) - 1)

    def money(comp: str, years: np.ndarray) -> tuple[float, float]:
        """(repair PV, lost-production PV per unit well rate) of these failures."""
        r = repair(cfg, REPAIR_KIND[comp])
        return r.cost * df[years].sum(), r.downtime * price * (df[years] * g[years]).sum()

    out = []
    for _ in range(n):
        constant = 0.0
        for w in field.wells:
            rp, lp = money("xmas_tree", events(rate(cfg, "xmas_tree")))
            constant += rp + lp * well_rate(cfg, w)
        site, site_size, connect, connect_size = {}, {}, {}, {}
        tie_lost = {}
        for s in field.sites:
            L = field.length(s, field.host)
            rf, lf = money("tieback_flowline", events(rate(cfg, "tieback_flowline", length=L)))
            ru, lu = money("tieback_umbilical", events(rate(cfg, "tieback_umbilical")))
            site[s], tie_lost[s] = rf + ru, lf + lu
            lam = {k: rate(cfg, "manifold", slots=k) for k in sizes}
            t = rng.uniform(0.0, life, rng.poisson(lam[sizes[-1]] * life))
            u = rng.uniform(size=len(t))
            years_all = np.minimum((t // YEAR).astype(int), len(df) - 1)
            man_lost = {}
            for k in sizes:
                rp, lp = money("manifold", years_all[u < lam[k] / lam[sizes[-1]]])
                site_size[s, k], man_lost[k] = rp, lp
            for w in field.wells:
                qw = well_rate(cfg, w)
                for k in sizes:
                    connect_size[w, s, k] = man_lost[k] * qw
        for w in field.wells:
            qw = well_rate(cfg, w)
            for s in field.sites:
                Lw = field.length(w, s)
                c = 0.0
                for comp in ("infield_flowline", "infield_umbilical"):
                    lam_c = rate(cfg, comp, length=Lw)
                    if lam_c > 0:
                        rp, lp = money(comp, events(lam_c))
                        c += rp + lp * qw
                connect[w, s] = c + tie_lost[s] * qw
        out.append(FailureCostCoefficients(constant, site, site_size, connect, connect_size))
    return out


def scenario_cost(c: FailureCostCoefficients, assignment: dict[str, str],
                  sizes: dict[str, int]) -> float:
    """Failure cost PV of a layout in one scenario (same formula as the MILP)."""
    return (c.constant + sum(c.site[s] + c.site_size[s, k] for s, k in sizes.items())
            + sum(c.connect[w, s] + c.connect_size[w, s, sizes[s]] for w, s in assignment.items()))


def default_sizes(cfg: dict, assignment: dict[str, str]) -> dict[str, int]:
    return {s: smallest_size(cfg, list(assignment.values()).count(s)) for s in set(assignment.values())}
