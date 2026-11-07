"""Step 7: Monte Carlo check of the expected-value model, and risk-averse (CVaR) layouts.

1. For candidate layouts: expected-value (EV) failure cost vs Monte Carlo mean, spread and
   CVaR; and run time of each method.
2. Histogram of failure-cost PV for the one-manifold and the split layout.
3. Risk weight rho from 0 to 1: optimal layout with CVaR in the MILP, then evaluated
   out-of-sample with an independent Monte Carlo run.

Usage:  python scripts/run_step7.py [path/to/config.yaml]
Writes: results/step7_validation.csv, results/step7_risk_sweep.csv, results/step7_histogram.png
"""
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from layout_rel.config import DEFAULT_CONFIG, REPO_ROOT, field_path, load_config, param, placeholders
from layout_rel.economics import npv_breakdown
from layout_rel.layout import load_field
from layout_rel.montecarlo import default_sizes, sample_scenarios, simulate_layout, summary
from layout_rel.optimizer import optimize_npv
from layout_rel.plotting import C_GRID, C_INK, C_INK_2, C_MANIFOLD, C_WELL

M = 1e6


def describe(a, sizes):
    return " + ".join(f"{s}({sizes[s]}-slot: {list(a.values()).count(s)})" for s in sorted(sizes))


def main(cfg_path=DEFAULT_CONFIG):
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    alpha = param(cfg, "risk.alpha")
    ck = f"cvar{int(alpha * 100)}"
    layouts = {
        "1 manifold (6)": {w: "M2" for w in field.wells},
        "2 manifolds (3+3)": {"W1": "M1", "W2": "M1", "W3": "M1", "W4": "M3", "W5": "M3", "W6": "M3"},
        "2 manifolds (4+2)": {"W1": "M1", "W2": "M1", "W3": "M1", "W4": "M1", "W5": "M3", "W6": "M3"},
    }

    # 1. EV vs MC
    rows, sims = [], {}
    for name, a in layouts.items():
        t = time.perf_counter()
        n = npv_breakdown(field, cfg, a)
        t_ev = time.perf_counter() - t
        ev = n["repair_cost"] + n["lost_production"]
        t = time.perf_counter()
        r = simulate_layout(field, cfg, a)
        t_mc = time.perf_counter() - t
        s = summary(r.total_pv, alpha)
        sims[name] = r
        rows.append({"layout": name, "EV failure PV [MUSD]": ev / M,
                     "MC mean [MUSD]": s["mean"] / M, "MC 95% CI +/- [MUSD]": 1.96 * s["se_mean"] / M,
                     "EV - MC [%]": 100 * (ev / s["mean"] - 1),
                     "MC std [MUSD]": s["std"] / M, "MC P90 [MUSD]": s["p90"] / M,
                     f"MC {ck.upper()} [MUSD]": s[ck] / M,
                     "EV NPV [MUSD]": n["npv"] / M,
                     "EV time [ms]": 1e3 * t_ev, "MC time [s]": t_mc})
    val = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(f"Expected value vs Monte Carlo ({param(cfg, 'montecarlo.n_sims')} field lives per layout):")
    print(val.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # 2. histogram
    fig, ax = plt.subplots(figsize=(9, 5))
    names = ["1 manifold (6)", "2 manifolds (3+3)"]
    data = [sims[k].total_pv / M for k in names]
    bins = np.linspace(0, np.percentile(np.concatenate(data), 99.8), 60)
    for name, x, col in zip(names, data, (C_WELL, C_MANIFOLD)):
        ax.hist(x, bins=bins, histtype="step", lw=2, color=col, label=name)
        cv = summary(x * M, alpha)[ck] / M
        ax.axvline(cv, color=col, lw=1.5, ls="--")
        ax.annotate(f"{ck.upper()} {cv:,.0f}", (cv, ax.get_ylim()[1] * (0.9 if col == C_WELL else 0.8)),
                    xytext=(5, 0), textcoords="offset points", color=C_INK_2, fontsize=9)
    ax.set_xlabel("Failure cost over field life, present value [MUSD]", color=C_INK_2)
    ax.set_ylabel("Simulated field lives", color=C_INK_2)
    ax.set_title("Same mean, different tail: grouping all wells on one manifold", loc="left",
                 color=C_INK, fontsize=11)
    ax.legend(frameon=False, labelcolor=C_INK_2)
    ax.grid(True, color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=C_INK_2)
    for sp in ax.spines.values():
        sp.set_color(C_GRID)
    fig.tight_layout()
    out = REPO_ROOT / "results"
    fig.savefig(out / "step7_histogram.png", dpi=200)

    # 3. risk sweep, evaluated out-of-sample
    scen = sample_scenarios(field, cfg)
    rows = []
    for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
        t = time.perf_counter()
        sol = optimize_npv(field, cfg, risk_weight=rho, scenarios=scen)
        t_opt = time.perf_counter() - t
        n = npv_breakdown(field, cfg, sol.assignment, sol.sizes)
        r = simulate_layout(field, cfg, sol.assignment, sol.sizes)
        s = summary(r.total_pv, alpha)
        rows.append({"rho": rho, "layout": describe(sol.assignment, sol.sizes),
                     "EV NPV [MUSD]": n["npv"] / M, "CAPEX [MUSD]": n["capex"] / M,
                     "MC mean failure PV [MUSD]": s["mean"] / M,
                     f"MC {ck.upper()} failure PV [MUSD]": s[ck] / M,
                     "solve time [s]": t_opt})
    sweep = pd.DataFrame(rows)
    print(f"\nRisk-averse layouts (CVaR alpha = {alpha}, {len(scen)} scenarios in the MILP; "
          "failure cost re-evaluated with an independent Monte Carlo run):")
    print(sweep.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    val.to_csv(out / "step7_validation.csv", index=False)
    sweep.to_csv(out / "step7_risk_sweep.csv", index=False)
    print(f"\nSaved {out / 'step7_histogram.png'}")
    todo = placeholders(cfg)
    if todo:
        print(f"NOTE: placeholders still in use: {', '.join(todo)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG)
