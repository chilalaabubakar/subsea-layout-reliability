"""Step 7: Monte Carlo check of the expected-value model, and risk-averse (CVaR) layouts.

1. For candidate layouts: expected-value (EV) failure cost vs Monte Carlo mean, spread and
   CVaR; and run time of each method.
2. Histogram of failure-cost PV for the one-manifold and the split layout.
3. Risk weight rho from 0 to 1: optimal layout with CVaR in the MILP, then evaluated
   out-of-sample with an independent Monte Carlo run.

The layouts compared are the case-1 optimum and every distinct optimum of the risk sweep.

Usage:  python scripts/run_step7.py [path/to/config.yaml]
Writes (in results/ or results/<config name>/): step7_validation.csv, step7_risk_sweep.csv,
        step7_histogram.png
"""
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from layout_rel.config import DEFAULT_CONFIG, field_path, load_config, param, placeholders, results_dir
from layout_rel.economics import npv_breakdown
from layout_rel.layout import load_field
from layout_rel.montecarlo import default_sizes, sample_scenarios, simulate_layout, summary
from layout_rel.optimizer import optimize_capex, optimize_npv
from layout_rel.plotting import C_GRID, C_INK, C_INK_2, C_MANIFOLD, C_WELL

M = 1e6


def describe(a, sizes):
    return " + ".join(f"{s}({sizes[s]}-slot: {list(a.values()).count(s)})" for s in sorted(sizes))


def main(cfg_path=DEFAULT_CONFIG):
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    alpha = param(cfg, "risk.alpha")
    ck = f"cvar{int(alpha * 100)}"
    out = results_dir(cfg_path)

    # risk sweep first: it defines the layouts worth comparing
    scen = sample_scenarios(field, cfg)
    sweep_rows, sols = [], {}
    for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
        t = time.perf_counter()
        sol = optimize_npv(field, cfg, risk_weight=rho, scenarios=scen)
        sols[rho] = (sol, time.perf_counter() - t)
    c1 = optimize_capex(field, cfg)
    layouts = {f"case 1: {describe(c1.assignment, c1.sizes)}": (c1.assignment, c1.sizes)}
    for rho, (sol, _) in sols.items():
        key = describe(sol.assignment, sol.sizes)
        if all(key not in k for k in layouts):
            layouts[f"rho {rho}: {key}"] = (sol.assignment, sol.sizes)

    # 1. EV vs MC
    rows, sims = [], {}
    for name, (a, sz) in layouts.items():
        t = time.perf_counter()
        n = npv_breakdown(field, cfg, a, sz)
        t_ev = time.perf_counter() - t
        ev = n["repair_cost"] + n["lost_production"]
        t = time.perf_counter()
        r = simulate_layout(field, cfg, a, sz)
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
    names = list(layouts)[:1] + list(layouts)[-1:]          # case 1 vs most risk-averse layout
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
    ax.set_title("Failure cost over field life: CAPEX-optimal vs most risk-averse layout", loc="left",
                 color=C_INK, fontsize=11)
    ax.legend(frameon=False, labelcolor=C_INK_2)
    ax.grid(True, color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=C_INK_2)
    for sp in ax.spines.values():
        sp.set_color(C_GRID)
    ax.legend(frameon=False, labelcolor=C_INK_2, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "step7_histogram.png", dpi=200)

    # 3. risk sweep, evaluated out-of-sample
    rows = []
    for rho, (sol, t_opt) in sols.items():
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
