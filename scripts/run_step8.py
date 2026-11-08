"""Step 8: sensitivity analysis.

1. One-at-a-time: every item in config `sensitivity` at low and high; case 1 and case 2
   re-solved each time. Tornado plot of the change in case-2 NPV and in failure-cost PV.
2. Switching map: vessel mobilisation time x manifold failure rate -> number of manifolds
   in the case-2 optimum and the value of reliability-aware design.

Usage:  python scripts/run_step8.py [--risk RHO] [path/to/config.yaml]
        --risk RHO  also run the one-at-a-time study with CVaR weight RHO (slower, ~5 min)
Writes (in results/ or results/<config name>/): step8_oat.csv, step8_tornado.png,
        step8_map.csv, step8_map.png (and step8_oat_risk.csv with --risk)
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from layout_rel.config import DEFAULT_CONFIG, field_path, load_config, param, placeholders, results_dir
from layout_rel.layout import load_field
from layout_rel.plotting import C_GRID, C_INK, C_INK_2, C_MANIFOLD, C_WELL
from layout_rel.sensitivity import grid, one_at_a_time, scale



def style(ax):
    ax.grid(True, axis="x", color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=C_INK_2)
    for sp in ax.spines.values():
        sp.set_color(C_GRID)


def tornado(df: pd.DataFrame, path: Path):
    d = df[df.parameter != "base"]
    cols = {"dNPV case 2 [MUSD]": "Change in NPV of case-2 optimum [MUSD]",
            "dfail": "Change in failure-cost PV [MUSD]"}
    base_fail = df.loc[df.parameter == "base", "failure PV case 2 [MUSD]"].iloc[0]
    d = d.assign(dfail=d["failure PV case 2 [MUSD]"] - base_fail)
    wide = d.pivot(index="parameter", columns="level", values="dNPV case 2 [MUSD]")
    order = (wide["high"] - wide["low"]).abs().sort_values().index.tolist()
    changed = set(d.loc[d["layout changed"], "parameter"])

    fig, axes = plt.subplots(1, 2, figsize=(13, 7.5), sharey=True)
    y = np.arange(len(order))
    for ax, (col, xlabel) in zip(axes, cols.items()):
        w = d.pivot(index="parameter", columns="level", values=col).loc[order]
        ax.barh(y + 0.18, w["low"], height=0.34, color=C_WELL, label="low value")
        ax.barh(y - 0.18, w["high"], height=0.34, color=C_MANIFOLD, label="high value")
        ax.axvline(0, color=C_INK_2, lw=1)
        ax.set_xlabel(xlabel, color=C_INK_2)
        style(ax)
    nice = {p: p.replace("_", " ").capitalize() for p in order}
    labels = [f"{nice[p]}  *" if p in changed else nice[p] for p in order]
    axes[0].set_yticks(y, labels)
    axes[0].set_title("NPV is driven by revenue inputs ...", loc="left", color=C_INK, fontsize=11)
    axes[1].set_title("... failure cost by reliability and logistics inputs", loc="left",
                      color=C_INK, fontsize=11)
    handles = [Line2D([], [], color=C_WELL, lw=8, label="low value"),
               Line2D([], [], color=C_MANIFOLD, lw=8, label="high value"),
               Line2D([], [], ls="", marker="$*$", color=C_INK, ms=8,
                      label="* = optimal layout changes (case 2 vs case 1)")]
    axes[1].legend(handles=handles, frameon=False, labelcolor=C_INK_2, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)


def switching_map(field, cfg, path: Path) -> pd.DataFrame:
    mob = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
    rate = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
    g = grid(field, cfg,
             ("mobilisation x", scale("vessels.msv_mobilisation", "vessels.hlv_mobilisation"), mob),
             ("manifold failure rate x", scale("reliability.manifold.failure_rate_per_h"), rate))
    n = g.pivot(index="manifold failure rate x", columns="mobilisation x", values="case 2 manifolds")
    v = g.pivot(index="manifold failure rate x", columns="mobilisation x",
                values="value of reliability-aware design [MUSD]")
    lab = g.pivot(index="manifold failure rate x", columns="mobilisation x", values="case 2 layout")

    blues = {1: "#e8f0fb", 2: "#9cc1ee", 3: "#2a78d6"}        # light -> dark, one hue
    fig, ax = plt.subplots(figsize=(10, 7.5))
    for i, r in enumerate(n.index):
        for j, m_ in enumerate(n.columns):
            k = int(n.loc[r, m_])
            ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=blues[k], edgecolor="white", lw=2))
            txt = f"{k}" if k == 1 else f"{k}\n+{v.loc[r, m_]:.0f}"
            ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center", fontsize=9,
                    color="white" if k == 3 else C_INK)
    j0, i0 = list(n.columns).index(1), list(n.index).index(1)
    ax.add_patch(plt.Rectangle((j0, i0), 1, 1, fill=False, edgecolor=C_INK, lw=2))
    ax.annotate("base case", (j0 + 0.5, i0 + 0.08), ha="center", fontsize=8, color=C_INK_2)
    ax.set_xlim(0, len(n.columns))
    ax.set_ylim(0, len(n.index))
    ax.set_xticks(np.arange(len(n.columns)) + 0.5, [f"\u00d7{c:g}" for c in n.columns])
    ax.set_yticks(np.arange(len(n.index)) + 0.5, [f"\u00d7{r:g}" for r in n.index])
    b = cfg["vessels"]
    ax.set_xlabel(f"Vessel mobilisation time (\u00d7 base: {b['msv_mobilisation']['value']:g} d light, "
                  f"{b['hlv_mobilisation']['value']:g} d heavy vessel)", color=C_INK_2)
    ax.set_ylabel(f"Manifold failure rate (\u00d7 base {cfg['reliability']['manifold']['failure_rate_per_h']['value'] * 1e6:g} per 10$^6$ h)",
                  color=C_INK_2)
    ax.set_title("Number of manifolds in the NPV-optimal layout\n"
                 "(cell text: manifolds, and NPV gain over the CAPEX-only layout in MUSD)",
                 loc="left", color=C_INK, fontsize=11)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=blues[k], edgecolor=C_GRID,
                             label=f"{k} manifold{'s' if k > 1 else ''}")
               for k in sorted(set(int(x) for x in n.values.ravel()))]
    ax.legend(handles=handles, frameon=False, labelcolor=C_INK_2, loc="upper left",
              bbox_to_anchor=(1.01, 1))
    ax.tick_params(colors=C_INK_2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=DEFAULT_CONFIG)
    ap.add_argument("--risk", type=float, default=None)
    args = ap.parse_args()
    cfg = load_config(Path(args.config))
    OUT = results_dir(args.config)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))

    pd.set_option("display.width", 250)
    show = ["parameter", "level", "setting", "case 2 layout", "layout changed",
            "NPV case 2 [MUSD]", "dNPV case 2 [MUSD]", "failure PV case 2 [MUSD]",
            "value of reliability-aware design [MUSD]"]
    oat = one_at_a_time(field, cfg)
    print("One-at-a-time sensitivity (expected-value objective):")
    print(oat[show].to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    oat.to_csv(OUT / "step8_oat.csv", index=False)
    tornado(oat, OUT / "step8_tornado.png")

    g = switching_map(field, cfg, OUT / "step8_map.png")
    g.to_csv(OUT / "step8_map.csv", index=False)
    print(f"\nSwitching map: {int((g['case 2 manifolds'] > 1).sum())} of {len(g)} cells split the field.")

    if args.risk is not None:
        oat_r = one_at_a_time(field, cfg, risk_weight=args.risk)
        print(f"\nOne-at-a-time sensitivity, risk-averse (rho = {args.risk}):")
        print(oat_r[show].to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
        oat_r.to_csv(OUT / "step8_oat_risk.csv", index=False)

    print(f"\nSaved {OUT / 'step8_tornado.png'} and {OUT / 'step8_map.png'}")
    todo = placeholders(cfg)
    if todo:
        print(f"NOTE: placeholders still in use: {', '.join(todo)}")


if __name__ == "__main__":
    main()
