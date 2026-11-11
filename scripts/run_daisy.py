"""Daisy chains: case 1 and case 2 with and without the option, on one field.

Three settings: separate tie-backs (the base model), daisy chains allowed, and daisy
chains allowed with the satellites' flow bypassing the hub manifold (a bound). For each
setting the case 1 and case 2 layouts are reported with CAPEX, expected failure cost and
NPV, and both layouts are simulated in full (mean and CVaR of the failure cost).

Usage:  python scripts/run_daisy.py [--critical-only] path/to/config.yaml
        (the config with daisy_chain false; the script switches the option itself)
        --critical-only  count only production-critical manifold failures
                         (values of sensitivity.manifold_critical_only, low)
Writes: results/<case>/step10_daisy.csv (step10_daisy_critical.csv with --critical-only)
"""
import copy
import sys
import time
from pathlib import Path

import pandas as pd

from layout_rel.config import field_path, load_config, param, results_dir
from layout_rel.economics import npv_breakdown
from layout_rel.layout import load_field
from layout_rel.montecarlo import simulate_layout, summary
from layout_rel.optimizer import optimize_capex, optimize_npv

M = 1e6
SETTINGS = {"separate tie-backs": (False, True), "daisy chain allowed": (True, True),
            "daisy chain, satellites bypass the hub manifold": (True, False)}


def describe(sol) -> str:
    parts = [f"{k}-slot at {s}" + (f" (into {sol.links[s]})" if s in sol.links else "") for s, k in sorted(sol.sizes.items())]
    return " + ".join(parts)


def main(cfg_path: Path, critical_only: bool = False) -> None:
    base = load_config(cfg_path)
    if critical_only:
        from layout_rel.sensitivity import apply
        base = apply(base, "manifold_critical_only", "low")
    field = load_field(field_path(base), param(base, "routing.length_factor"))
    beta = param(base, "risk.alpha")
    rows = []
    for name, (daisy, stops) in SETTINGS.items():
        cfg = copy.deepcopy(base)
        cfg["routing"]["daisy_chain"]["value"] = daisy
        cfg["routing"]["hub_manifold_stops_satellites"]["value"] = stops
        t = time.perf_counter()
        sols = {"case 1": optimize_capex(field, cfg), "case 2": optimize_npv(field, cfg)}
        t = time.perf_counter() - t
        for case, sol in sols.items():
            n = npv_breakdown(field, cfg, sol.assignment, sol.sizes, sol.links)
            st = summary(simulate_layout(field, cfg, sol.assignment, sol.sizes, links=sol.links).total_pv, beta)
            rows.append({"setting": name, "case": case, "layout": describe(sol), "manifolds": len(sol.sizes),
                         "chains": len(sol.links), "CAPEX [MUSD]": n["capex"] / M,
                         "failure PV [MUSD]": (n["repair_cost"] + n["lost_production"]) / M, "NPV [MUSD]": n["npv"] / M,
                         "MC mean [MUSD]": st["mean"] / M, f"MC CVaR{int(beta * 100)} [MUSD]": st[f"cvar{int(beta * 100)}"] / M,
                         "solve time both cases [s]": t})
    df = pd.DataFrame(rows)
    out = results_dir(cfg_path) / ("step10_daisy_critical.csv" if critical_only else "step10_daisy.csv")
    df.to_csv(out, index=False)
    pd.set_option("display.width", 260); pd.set_option("display.max_colwidth", 90)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    print(f"Saved {out}")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(Path([a for a in args if not a.startswith("--")][0]), "--critical-only" in args)
