"""Two assumptions of the base case, tested as whole cases.

1. Deferred production. The base case counts production shut in by a failure as lost. Here a
   share of it is produced later (in the last year of field life, or one year after the outage).
2. Critical manifold failures. The base case lets every recorded manifold failure stop
   production. Here only failures in the production path of the manifold module count.

For each case (config: assumption_checks.cases) the script gives
- the expected-value optimum (case 2) with its failure cost and NPV;
- the full-simulation mean and CVaR of that layout;
- the risk weight from which a split is the best layout, found by ranking every feasible
  layout on the reference sample (risk.n_reference scenarios, same seed in every case).

Usage:  python scripts/run_assumptions.py [--jobs N] [path/to/config.yaml]
        (default: config/solveig_weather.yaml)
Writes: results/<case>/step8_assumptions.csv
"""
import argparse
import copy
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from layout_rel.config import REPO_ROOT, field_path, load_config, param, param_raw, results_dir
from layout_rel.economics import npv_breakdown
from layout_rel.layout import load_field
from layout_rel.montecarlo import simulate_layout, summary
from layout_rel.optimizer import optimize_npv
from layout_rel.saa import describe, layout_table, reference_sample

M = 1e6


def case_config(cfg: dict, changes: dict) -> dict:
    c = copy.deepcopy(cfg)
    for key, value in changes.items():
        node = c
        for part in key.split("."):
            node = node[part]
        node["value"] = value
    return c


def run_case(args) -> dict:
    cfg_path, name, changes = args
    t = time.perf_counter()
    base = load_config(cfg_path)
    cfg = case_config(base, changes)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    beta = param(cfg, "risk.alpha")
    ck = f"cvar{int(beta * 100)}"

    sol = optimize_npv(field, cfg)                                   # expected-value optimum
    n = npv_breakdown(field, cfg, sol.assignment, sol.sizes)
    sim = summary(simulate_layout(field, cfg, sol.assignment, sol.sizes).total_pv, beta)

    tab = layout_table(field, cfg, reference_sample(field, cfg))     # every layout, same scenarios
    first = tab.best(0.0)
    switch = next((w / 1000 for w in range(1001) if tab.best(w / 1000) != first), None)
    top = tab.best(1.0)
    return {"case": name,
            "deferred share": param(cfg, "production.deferred_fraction"),
            "deferred volume recovered": ("-" if not param(cfg, "production.deferred_fraction") else
                                          "last year of field life" if param_raw(cfg, "production.deferral_delay") is None
                                          else f"{param_raw(cfg, 'production.deferral_delay'):g} yr after the outage"),
            "critical share of manifold failures": param(cfg, "reliability.manifold.critical_fraction"),
            "per-slot share f": param(cfg, "reliability.manifold.slot_fraction"),
            "EV layout": describe(sol.assignment, sol.sizes),
            "repair PV [MUSD]": n["repair_cost"] / M, "lost production PV [MUSD]": n["lost_production"] / M,
            "failure PV [MUSD]": (n["repair_cost"] + n["lost_production"]) / M, "NPV [MUSD]": n["npv"] / M,
            "MC mean failure PV [MUSD]": sim["mean"] / M, f"MC {ck.upper()} [MUSD]": sim[ck] / M,
            "split is best from w": switch,
            "best layout at w = 1": describe(*tab.layouts[top]),
            "cost of the split at w = 1 minus single manifold [MUSD]": (tab.objective(1.0)[top] - tab.objective(1.0)[first]) / M,
            "time [s]": time.perf_counter() - t}


def main(cfg_path: Path, jobs: int) -> None:
    cfg = load_config(cfg_path)
    cases = param_raw(cfg, "assumption_checks.cases")
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        rows = list(ex.map(run_case, [(cfg_path, name, changes) for name, changes in cases.items()]))
    df = pd.DataFrame(rows)
    out = results_dir(cfg_path) / "step8_assumptions.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    print(df.drop(columns=["time [s]"]).T.to_string(float_format=lambda v: f"{v:,.2f}"))
    print(f"Saved {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("config", nargs="?", default=str(REPO_ROOT / "config" / "solveig_weather.yaml"))
    a = ap.parse_args()
    main(Path(a.config), a.jobs)
