"""Sample-average checks of the risk-averse (CVaR) MILP.

The MILP sees the tail of the failure cost only through N sampled scenarios, so its
answer depends on the sample. Following Kleywegt, Shapiro & Homem-de-Mello (2002,
SIAM J. Optim. 12:479-502):

1. solve the MILP for several independent samples (replications) and see which layouts win;
2. compare the candidate layouts on one much larger reference sample.

The fields here are small enough to do (2) for EVERY feasible layout. That gives the
layout that is best on the reference sample for each risk weight, and the regret of
each MILP answer against it. All layouts are evaluated on the same scenarios (common
random numbers), so differences between layouts are far less noisy than the levels.

Objective, as in ``optimizer.build_npv_model`` (minimised, USD present value):
    CAPEX (1 + o A) + (1 - w) E[F] + w CVaR_beta(F)
with E[F] the analytical expected failure cost and CVaR taken over the scenarios.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from .config import param
from .economics import annuity_factors, capex_breakdown, manifold_sizes
from .layout import Field
from .maintenance import FailureCostCoefficients, failure_cost_coefficients
from .montecarlo import cvar_lp, default_sizes, sample_scenarios, scenario_cost

Layout = tuple[dict[str, str], dict[str, int]]          # ({well: site}, {site: slots})


def describe(assignment: dict[str, str], sizes: dict[str, int]) -> str:
    return " + ".join(f"{s}({sizes[s]}-slot: {list(assignment.values()).count(s)})" for s in sorted(sizes))


def assignment_text(assignment: dict[str, str]) -> str:
    """'well:site;well:site;...' in well order: one unambiguous string per layout."""
    return ";".join(f"{w}:{s}" for w, s in sorted(assignment.items()))


def feasible_layouts(field: Field, cfg: dict) -> list[Layout]:
    """Every well-to-site assignment that fits the largest manifold, with the smallest
    manifold that fits each open site (a larger one costs more and fails more often)."""
    biggest = max(manifold_sizes(cfg))
    out = []
    for combo in itertools.product(field.sites, repeat=len(field.wells)):
        if all(combo.count(s) <= biggest for s in field.sites):
            a = dict(zip(field.wells, combo))
            out.append((a, default_sizes(cfg, a)))
    return out


@dataclass
class ScenarioArrays:
    """Scenarios of ``montecarlo.sample_scenarios`` as arrays (first axis: scenario)."""
    wells: list[str]
    sites: list[str]
    sizes: list[int]
    constant: np.ndarray        # (M,)
    site: np.ndarray            # (M, S)
    site_size: np.ndarray       # (M, S, K)
    connect: np.ndarray         # (M, W, S)
    connect_size: np.ndarray    # (M, W, S, K)

    @classmethod
    def from_scenarios(cls, field: Field, cfg: dict, scen: list[FailureCostCoefficients]) -> "ScenarioArrays":
        W, S, K = list(field.wells), list(field.sites), list(manifold_sizes(cfg))
        return cls(W, S, K,
                   np.array([c.constant for c in scen]),
                   np.array([[c.site[s] for s in S] for c in scen]),
                   np.array([[[c.site_size[s, k] for k in K] for s in S] for c in scen]),
                   np.array([[[c.connect[w, s] for s in S] for w in W] for c in scen]),
                   np.array([[[[c.connect_size[w, s, k] for k in K] for s in S] for w in W] for c in scen]))

    @classmethod
    def concat(cls, parts: list["ScenarioArrays"]) -> "ScenarioArrays":
        p = parts[0]
        return cls(p.wells, p.sites, p.sizes, *(np.concatenate([getattr(q, f) for q in parts])
                                                 for f in ("constant", "site", "site_size", "connect", "connect_size")))

    def __len__(self) -> int:
        return len(self.constant)

    def cost(self, assignment: dict[str, str], sizes: dict[str, int]) -> np.ndarray:
        """Failure cost PV of a layout in every scenario (same formula as ``scenario_cost``)."""
        si = {s: i for i, s in enumerate(self.sites)}
        ki = {k: i for i, k in enumerate(self.sizes)}
        f = self.constant.copy()
        for s, k in sizes.items():
            f += self.site[:, si[s]] + self.site_size[:, si[s], ki[k]]
        for wi, w in enumerate(self.wells):
            s = assignment[w]
            f += self.connect[:, wi, si[s]] + self.connect_size[:, wi, si[s], ki[sizes[s]]]
        return f


def reference_sample(field: Field, cfg: dict, n: int | None = None, seed: int | None = None,
                     chunk: int = 5000) -> ScenarioArrays:
    """Large scenario sample as arrays, drawn in chunks (seed, seed + 1, ...) to save memory."""
    n = int(n or param(cfg, "risk.n_reference"))
    seed = param(cfg, "risk.reference_seed") if seed is None else seed
    parts, i = [], 0
    while n > 0:
        m = min(chunk, n)
        parts.append(ScenarioArrays.from_scenarios(field, cfg, sample_scenarios(field, cfg, n=m, seed=seed + i)))
        n, i = n - m, i + 1
    return ScenarioArrays.concat(parts)


@dataclass
class LayoutTable:
    """Deterministic and sampled cost terms of every feasible layout (USD present value)."""
    layouts: list[Layout]
    fixed: np.ndarray           # CAPEX (1 + o A)
    ev: np.ndarray              # analytical expected failure cost
    cvar: np.ndarray            # CVaR_beta of the failure cost over the sample

    def objective(self, w: float) -> np.ndarray:
        return self.fixed + (1 - w) * self.ev + w * self.cvar

    def best(self, w: float) -> int:
        return int(np.argmin(self.objective(w)))

    def index(self, assignment: dict[str, str], sizes: dict[str, int] | None = None) -> int:
        return next(i for i, (a, s) in enumerate(self.layouts) if a == assignment and sizes in (None, s))

    def index_of_text(self, text: str) -> int:
        return self.index(dict(pair.split(":") for pair in text.split(";")))


def layout_table(field: Field, cfg: dict, scen: ScenarioArrays, layouts: list[Layout] | None = None) -> LayoutTable:
    layouts = layouts or feasible_layouts(field, cfg)
    a_rep, a_prod = annuity_factors(cfg)
    f_ev = failure_cost_coefficients(field, cfg, repair_weight=a_rep, production_weight=a_prod)
    opex = param(cfg, "economics.opex_fraction_of_capex") * a_rep
    beta = param(cfg, "risk.alpha")
    fixed = np.array([capex_breakdown(field, cfg, a, s)["total"] * (1 + opex) for a, s in layouts])
    ev = np.array([scenario_cost(f_ev, a, s) for a, s in layouts])
    cv = np.array([cvar_lp(scen.cost(a, s), beta) for a, s in layouts])
    return LayoutTable(layouts, fixed, ev, cv)
