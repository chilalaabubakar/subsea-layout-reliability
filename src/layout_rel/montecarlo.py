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

Weather wait per failure (``WeatherWaits``): if the config names an hourly wait file
(``montecarlo.weather_wait_file``, written by scripts/weather_windows.py), each failure
waits as long as the hindcast says for the hour its vessel is ready (failure time +
mobilisation), so winter failures wait longer than summer ones. Without the file every
failure uses the mean wait (``maintenance.<kind>.weather_wait_days``), as the EV model does.
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import REPO_ROOT, param, param_raw
from .economics import (discount_factors, lost_production_weights, manifold_sizes, production_profile,
                        smallest_size)
from .layout import Field
from .maintenance import FailureCostCoefficients, Repair, repair, well_rate
from .reliability import REPAIR_KIND, failure_modes, rate
from .units import HOUR, YEAR


@functools.lru_cache(maxsize=4)
def _hourly_wait_table(path: str) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """({repair kind: wait [h] per hindcast hour}, indices of each 1 January 00:00)."""
    t = pd.read_csv(path, parse_dates=["time"])
    waits = {c[:-2]: t[c].to_numpy(float) for c in t.columns if c.endswith("_h")}
    starts = np.flatnonzero((t.time.dt.month == 1) & (t.time.dt.day == 1) & (t.time.dt.hour == 0))
    return waits, starts


@dataclass
class WeatherWaits:
    """Weather wait of a repair by the hindcast hour at which its vessel is ready.

    The hindcast is used as a loop: a simulated field life starts on 1 January of a
    randomly drawn hindcast year (``draw_offsets``) and runs through the record, back to
    its first year after the last. Each wait series is scaled so that its mean equals the
    config's mean wait for that repair kind; the expected-value model and the simulation
    then use the same mean, also in sensitivity runs that scale the wait.
    """
    wait: dict[str, np.ndarray]    # repair kind -> wait [s] for each hindcast hour
    year_start: np.ndarray         # index of 1 January 00:00 of each hindcast year

    def draw_offsets(self, rng: np.random.Generator, n: int | None = None):
        return rng.choice(self.year_start, size=n)

    def downtime(self, kind: str, r: Repair, times: np.ndarray, offset: int) -> np.ndarray:
        """Downtime [s] of failures at field times ``times`` [s]: mobilisation + wait + repair."""
        w = self.wait[kind]
        ready = ((np.asarray(times) + r.mobilisation) // HOUR).astype(np.int64)
        return r.mobilisation + w[(offset + ready) % len(w)] + r.active


def weather_waits(cfg: dict) -> WeatherWaits | None:
    """Hourly waits named by ``montecarlo.weather_wait_file``, or None (mean wait for all)."""
    path = param_raw(cfg, "montecarlo.weather_wait_file")
    if not path:
        return None
    hours, starts = _hourly_wait_table(str(REPO_ROOT / path))
    wait = {}
    for kind, h in hours.items():
        mean = param(cfg, f"maintenance.{kind}.weather_wait_days")        # s
        wait[kind] = h * (mean / h.mean()) if h.mean() > 0 else np.zeros_like(h)
    return WeatherWaits(wait, starts)


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


def cvar_lp(x: np.ndarray, alpha: float) -> float:
    """CVaR exactly as the MILP's linear form defines it on a sample (Rockafellar & Uryasev):
    min over eta of eta + mean(max(x - eta, 0)) / (1 - alpha). Equal to ``cvar`` when
    (1 - alpha) * len(x) is a whole number; otherwise the last tail scenario counts in part."""
    xs = np.sort(np.asarray(x))[::-1]
    k = len(xs) * (1 - alpha)
    whole = int(math.floor(k + 1e-9))
    tail = xs[:whole].sum() + ((k - whole) * xs[whole] if whole < len(xs) and k - whole > 1e-9 else 0.0)
    return float(tail / k)


def summary(x: np.ndarray, alpha: float) -> dict[str, float]:
    x = np.asarray(x)
    return {"mean": float(x.mean()), "std": float(x.std(ddof=1)),
            "se_mean": float(x.std(ddof=1) / math.sqrt(len(x))),
            "p50": float(np.percentile(x, 50)), "p90": float(np.percentile(x, 90)),
            f"cvar{int(alpha * 100)}": cvar(x, alpha), "max": float(x.max())}


def _year_tables(cfg: dict) -> tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    """Discount factors, production profile, field life [s], and the value weights of lost
    production (= discount factors unless part of the shut-in volume is deferred)."""
    df = np.array(discount_factors(cfg))
    g = np.array(production_profile(cfg))
    return df, g, len(df) * YEAR, np.array(lost_production_weights(cfg))


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
    df, g, life, lw = _year_tables(cfg)
    price = param(cfg, "production.oil_price")
    modes = [m for m in failure_modes(field, cfg, assignment, sizes) if m.rate > 0]
    reps = [repair(cfg, m.repair_kind) for m in modes]
    q = {w: well_rate(cfg, w) for w in field.wells}

    repair_pv, lost_pv = np.zeros(n), np.zeros(n)
    downtime, failures = np.zeros(n), np.zeros(n)
    counts = rng.poisson([m.rate * life for m in modes], size=(n, len(modes)))
    ww = weather_waits(cfg)
    offsets = ww.draw_offsets(rng, n) if ww else None        # hindcast year in which each life starts
    for i in range(n):
        outages: dict[str, list[tuple[float, float]]] = {w: [] for w in field.wells}
        for j in np.nonzero(counts[i])[0]:
            m, r = modes[j], reps[j]
            times = rng.uniform(0.0, life, counts[i, j])     # Poisson: uniform given count
            years = np.minimum((times // YEAR).astype(int), len(df) - 1)
            if ww is None:                                   # every failure: mean weather wait
                repair_pv[i] += r.cost * df[years].sum()
                ends = times + r.downtime
            else:                                            # wait of the hour the vessel is ready
                down = ww.downtime(m.repair_kind, r, times, offsets[i])
                repair_pv[i] += (r.cost_at(down) * df[years]).sum()
                ends = times + down
            failures[i] += len(times)
            for t, e in zip(times.tolist(), ends.tolist()):
                for w in m.wells:
                    outages[w].append((t, e))
        for w, iv in outages.items():
            pv, d = _lost_pv_of_intervals(iv, q[w], price, lw, g, life)
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
    df, g, life, lw = _year_tables(cfg)
    price = param(cfg, "production.oil_price")
    sizes = manifold_sizes(cfg)

    ww = weather_waits(cfg)
    reps = {comp: repair(cfg, kind) for comp, kind in REPAIR_KIND.items()}
    offset = 0

    def events(lam: float) -> np.ndarray:
        """Failure times [s] in one field life."""
        return rng.uniform(0.0, life, rng.poisson(lam * life))

    def money(comp: str, t: np.ndarray) -> tuple[float, float]:
        """(repair PV, lost-production PV per unit well rate) of failures at times ``t``."""
        r = reps[comp]
        years = np.minimum((t // YEAR).astype(int), len(df) - 1)
        if ww is None:
            return r.cost * df[years].sum(), r.downtime * price * (lw[years] * g[years]).sum()
        down = ww.downtime(REPAIR_KIND[comp], r, t, offset)
        return (r.cost_at(down) * df[years]).sum(), price * (down * lw[years] * g[years]).sum()

    out = []
    for _ in range(n):
        if ww is not None:
            offset = int(ww.draw_offsets(rng))               # hindcast year in which this life starts
        constant = 0.0
        for w in field.wells:
            rp, lp = money("xmas_tree", events(rate(cfg, "xmas_tree")))
            constant += rp + lp * well_rate(cfg, w)
        site, site_size, connect, connect_size = {}, {}, {}, {}
        tie_lost = {}
        for s in field.sites:
            L = field.length(s, field.host)
            rf, lf = money("tieback_flowline", events(rate(cfg, "tieback_flowline", length=L)))
            ru, lu = money("tieback_umbilical", events(rate(cfg, "tieback_umbilical", length=L)))
            site[s], tie_lost[s] = rf + ru, lf + lu
            lam = {k: rate(cfg, "manifold", slots=k) for k in sizes}
            t = rng.uniform(0.0, life, rng.poisson(lam[sizes[-1]] * life))
            u = rng.uniform(size=len(t))
            man_lost = {}
            for k in sizes:
                rp, lp = money("manifold", t[u < lam[k] / lam[sizes[-1]]])
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
