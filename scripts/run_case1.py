"""Case 1: CAPEX-only optimal layout for the field in the base-case config.

Usage:  python scripts/run_case1.py [path/to/config.yaml]
Writes: results/case1_layout.png, results/case1_capex.csv
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from layout_rel.config import DEFAULT_CONFIG, REPO_ROOT, field_path, load_config, param, placeholders
from layout_rel.economics import capex_breakdown
from layout_rel.layout import load_field
from layout_rel.optimizer import optimize_capex
from layout_rel.plotting import plot_layout


def main(cfg_path=DEFAULT_CONFIG):
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    sol = optimize_capex(field, cfg)
    capex = capex_breakdown(field, cfg, sol.assignment)

    out = REPO_ROOT / "results"
    out.mkdir(exist_ok=True)

    print(f"Field: {field.name}")
    print(f"Solver status: {sol.status}")
    print(f"Open manifolds: {', '.join(sol.open_sites)}")
    for s in sol.open_sites:
        ws = [w for w, t in sol.assignment.items() if t == s]
        print(f"  {s}: {', '.join(ws)}")
    df = pd.DataFrame({"item": list(capex), "USD": list(capex.values())})
    df["MUSD"] = df["USD"] / 1e6
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    df.to_csv(out / "case1_capex.csv", index=False)

    fig, ax = plt.subplots(figsize=(8.5, 7))
    plot_layout(field, sol.assignment, ax=ax,
                title=f"Case 1 - CAPEX-only optimum: {capex['total']/1e6:,.0f} MUSD")
    fig.tight_layout()
    fig.savefig(out / "case1_layout.png", dpi=200)
    print(f"Saved {out / 'case1_layout.png'}")

    todo = placeholders(cfg)
    if todo:
        print(f"\nNOTE: {len(todo)} parameter(s) are still placeholders "
              "(see `python -m layout_rel.config`).")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG)
