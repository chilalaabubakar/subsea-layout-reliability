"""Rank every feasible layout with the FULL simulation (overlapping outages merged, dated
weather waits), not with the linear scenario form the MILP uses.

Every layout is simulated with the same seed (common random numbers). For risk weight w the
cost of a layout is  CAPEX (1 + o A) + (1 - w) mean + w CVaR,  with mean and CVaR of the
simulated failure cost. The script reports the best layout by w and, for comparison, the
analytical expected failure cost of each layout.

Usage:  python scripts/run_full_ranking.py [--jobs N] [path/to/config.yaml]
        (default: config/solveig_weather.yaml; about 2 s per layout and core)
Writes: results/<case>/step7_full_ranking.csv (every layout), step7_full_ranking_best.csv
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from layout_rel.config import REPO_ROOT, field_path, load_config, param, results_dir
from layout_rel.economics import annuity_factors, capex_breakdown
from layout_rel.layout import load_field
from layout_rel.maintenance import failure_cost_coefficients
from layout_rel.montecarlo import scenario_cost, simulate_layout, summary
from layout_rel.saa import assignment_text, describe, feasible_layouts

M = 1e6


def chunk(args):
    cfg_path, lo, hi = args
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    beta = param(cfg, "risk.alpha")
    a_rep, a_prod = annuity_factors(cfg)
    f_ev = failure_cost_coefficients(field, cfg, repair_weight=a_rep, production_weight=a_prod)
    opex = param(cfg, "economics.opex_fraction_of_capex") * a_rep
    rows = []
    for a, s in feasible_layouts(field, cfg)[lo:hi]:
        st = summary(simulate_layout(field, cfg, a, s).total_pv, beta)      # same seed for every layout
        rows.append({"layout": describe(a, s), "assignment": assignment_text(a), "manifolds": len(s),
                     "fixed cost CAPEX(1+oA) [MUSD]": capex_breakdown(field, cfg, a, s)["total"] * (1 + opex) / M,
                     "expected failure cost [MUSD]": scenario_cost(f_ev, a, s) / M,
                     "MC mean [MUSD]": st["mean"] / M, "MC CVaR [MUSD]": st[f"cvar{int(beta * 100)}"] / M})
    return rows


def main(cfg_path: Path, jobs: int) -> None:
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    n = len(feasible_layouts(field, cfg))
    step = max(1, n // (jobs * 8))
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        rows = [r for part in ex.map(chunk, [(cfg_path, i, min(i + step, n)) for i in range(0, n, step)]) for r in part]
    df = pd.DataFrame(rows)
    out = results_dir(cfg_path)
    df.to_csv(out / "step7_full_ranking.csv", index=False, float_format="%.4f")
    fixed, mean, cv = (df[c].to_numpy() for c in ("fixed cost CAPEX(1+oA) [MUSD]", "MC mean [MUSD]", "MC CVaR [MUSD]"))
    obj = lambda w: fixed + (1 - w) * mean + w * cv
    best, i0 = [], None
    for w in np.round(np.arange(0, 1.0001, 0.01), 2):
        i = int(np.argmin(obj(w)))
        if i != i0:
            o = np.sort(obj(w))
            best.append({"from w": w, "best layout (full simulation)": df.layout[i], "assignment": df.assignment[i],
                         "cost at that w [MUSD]": o[0], "margin to second best [MUSD]": o[1] - o[0]})
            i0 = i
    one = int(np.argmin(obj(0.0)))
    two = df.index[df.manifolds == 2]
    j = two[int(np.argmin(obj(1.0)[two]))]
    print(pd.DataFrame(best).to_string(index=False))
    print(f"\nat w = 1: best single-manifold layout {df.layout[one]} costs {obj(1.0)[one]:.1f} MUSD; "
          f"best two-manifold layout {df.layout[j]} ({df.assignment[j]}) costs {obj(1.0)[j]:.1f} MUSD")
    pd.DataFrame(best).to_csv(out / "step7_full_ranking_best.csv", index=False)
    print(f"Saved {out / 'step7_full_ranking.csv'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("config", nargs="?", default=str(REPO_ROOT / "config" / "solveig_weather.yaml"))
    a = ap.parse_args()
    main(Path(a.config), a.jobs)
