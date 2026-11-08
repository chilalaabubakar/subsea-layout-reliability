"""Publication-ready versions of the paper's data figures (Figures 4-9), in the
figures4papers house style (see src/layout_rel/pubstyle.py).

Reads saved results where they exist and re-runs only the quick pieces (layouts,
20,000-life Monte Carlo of two layouts, about 1 min in total).

Usage:  python scripts/make_paper_figures.py [path/to/config.yaml]
        (default: config/solveig_weather.yaml, the paper's base case)
Writes: figures/fig4_solveig_map, fig5_weather_wait, fig6_mc_distribution,
        fig7_layouts, fig8_tornado, fig9_switching_map  (.png at 300 dpi and .pdf)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from layout_rel.config import REPO_ROOT, field_path, load_config, param, results_dir
from layout_rel.layout import load_field
from layout_rel.montecarlo import cvar, sample_scenarios, simulate_layout
from layout_rel.optimizer import optimize_capex, optimize_npv
from layout_rel.plotting import plot_layout
from layout_rel.pubstyle import PALETTE, FigureStyle, apply_publication_style, finalize_figure

import matplotlib.pyplot as plt  # noqa: E402  (backend set in pubstyle)
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

M = 1e6
OUT = REPO_ROOT / "figures"
P = PALETTE

# readable names for the one-at-a-time inputs (figure text only)
NICE = {
    "manifold_failure_rate": "Manifold failure rate", "all_failure_rates": "All failure rates",
    "mobilisation_time": "Vessel mobilization time", "well_rate": "Well rate",
    "oil_price": "Oil price", "weather_wait": "Weather waits",
    "umbilical_failure_rate": "Umbilical failure rate", "decline_rate": "Decline rate",
    "discount_rate": "Discount rate", "plateau_years": "Plateau length",
    "tree_failure_rate": "Tree failure rate", "vessel_day_rates": "Vessel day rates",
    "repair_time": "Active repair time", "field_life": "Field life",
    "weather_allowance": "Weather allowance", "slot_fraction": "Per-slot share of manifold rate",
}


def fig4_map(field, out):
    fig, ax = plt.subplots(figsize=(8.5, 7))
    plot_layout(field, {}, ax=ax, show_candidates=True)
    ax.legend_.remove() if ax.get_legend() else None
    handles = [Line2D([], [], marker="^", ls="", color=P["grey_mid"], ms=9, label="Production well"),
               Line2D([], [], marker="s", ls="", mfc="none", mec="#A3A29C", mew=1.5, ms=9,
                      label="Candidate manifold site")]
    ax.legend(handles=handles, loc="upper left", fontsize=12)
    finalize_figure(fig, out)


def fig5_weather(out):
    mon = pd.read_csv(REPO_ROOT / "results" / "weather_solveig_monthly.csv")
    mon = mon[mon["mode"] == "lifts"]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.axvspan(0.5, 3.5, color=P["neutral"], alpha=0.35, lw=0)
    ax.axvspan(9.5, 12.5, color=P["neutral"], alpha=0.35, lw=0)
    ax.text(2, 41, "Winter", ha="center", va="top", fontsize=12, color=P["grey_dark"])
    ax.text(11, 41, "Winter", ha="center", va="top", fontsize=12, color=P["grey_dark"])
    for kind, col, lab in (("manifold", P["blue_main"], "Heavy repair (heavy-lift vessel, 2 lifts)"),
                           ("xmas_tree", P["teal"], "Tree repair (light vessel, 1 lift)")):
        d = mon[mon.repair == kind].sort_values("month")
        ax.plot(d.month, d.mean_wait_d, marker="o", ms=7, lw=2.5, color=col, label=lab)
    ax.set_xticks(range(1, 13), list("JFMAMJJASOND"))
    ax.set_xlim(0.5, 12.5)
    ax.set_ylim(0, 42)
    ax.set_xlabel("Month of call-out")
    ax.set_ylabel("Mean wait for a weather window (d)")
    ax.legend(loc="upper center", fontsize=12, bbox_to_anchor=(0.5, 0.93))
    finalize_figure(fig, out)


def fig6_mc(field, cfg, layouts, out):
    alpha = param(cfg, "risk.alpha")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    data = {k: simulate_layout(field, cfg, a, s).total_pv / M for k, (a, s) in layouts.items()}
    top = np.percentile(np.concatenate(list(data.values())), 99.5)
    bins = np.linspace(0, top, 60)
    cols = {"CAPEX-optimal (one 6-slot manifold)": P["red_strong"],
            "Risk-averse (4-slot + 2-slot manifolds)": P["blue_main"]}
    handles = []
    for k, x in data.items():
        ax.hist(x, bins=bins, histtype="step", lw=2.5, color=cols[k])
        cv = cvar(x, alpha)
        ax.axvline(cv, color=cols[k], lw=2, ls="--")
        handles.append(Line2D([], [], color=cols[k], lw=2.5, label=k))
        handles.append(Line2D([], [], color=cols[k], lw=2, ls="--",
                              label=f"   CVaR$_{{{int(alpha * 100)}}}$ = {cv:,.0f} MUSD"))
    ax.set_xlim(0, top)
    ax.set_xlabel("Failure cost over field life, PV (MUSD)")
    ax.set_ylabel("Simulated field lives")
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=11)
    finalize_figure(fig, out)


def fig7_layouts(field, layouts, out):
    fig, axes = plt.subplots(1, 2, figsize=(12, 8))
    for ax, (k, (a, s)) in zip(axes, layouts.items()):
        plot_layout(field, a, ax=ax, sizes=s, zoom=True)
        if ax.get_legend():
            ax.get_legend().remove()
        ax.set_title(k, loc="left", fontsize=14)
    handles = [Line2D([], [], marker="^", ls="", color=P["grey_mid"], ms=9, label="Well"),
               Line2D([], [], marker="s", ls="", color=P["blue_main"], ms=9, label="Open manifold"),
               Line2D([], [], marker="s", ls="", mfc="none", mec="#A3A29C", mew=1.5, ms=9, label="Unused site"),
               Line2D([], [], color=P["grey_dark"], lw=1.2, label="Infield lines"),
               Line2D([], [], color=P["ink"], lw=2, label="Tie-back")]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=12)
    fig.tight_layout(pad=2, rect=(0, 0.06, 1, 1))
    for fmt in ("png", "pdf"):
        fig.savefig(Path(out).with_suffix("." + fmt), dpi=300, facecolor="white")
    plt.close(fig)


def fig8_tornado(res, out):
    d = pd.read_csv(res / "step8_oat.csv")
    base = d.loc[d.parameter == "base", "failure PV case 2 [MUSD]"].iloc[0]
    d = d[d.parameter != "base"].assign(df=lambda t: t["failure PV case 2 [MUSD]"] - base)
    w = d.pivot(index="parameter", columns="level", values="df")
    w = w[(w.abs() > 0.5).any(axis=1)]
    order = (w.max(axis=1) - w.min(axis=1)).sort_values().index
    changed = set(d.loc[d["layout changed"], "parameter"])
    w = w.loc[order]
    y = np.arange(len(w))
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(y + 0.19, w["low"], height=0.36, color=P["blue_secondary"], alpha=0.45,
            edgecolor="black", lw=1, label="Low value")
    ax.barh(y - 0.19, w["high"], height=0.36, color=P["blue_main"], edgecolor="black", lw=1,
            label="High value")
    ax.axvline(0, color=P["ink"], lw=1.5)
    ax.set_yticks(y, [NICE.get(p, p) + ("  *" if p in changed else "") for p in w.index])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel(f"Change in failure-cost PV from base {base:,.0f} MUSD (MUSD)")
    ax.legend(loc="lower right", fontsize=12, title="* optimal layout changes", title_fontsize=11)
    finalize_figure(fig, out)


def fig9_map(res, out):
    g = pd.read_csv(res / "step8_map.csv")
    gain = g.pivot(index="manifold failure rate x", columns="mobilisation x",
                   values="value of reliability-aware design [MUSD]")
    n = g.pivot(index="manifold failure rate x", columns="mobilisation x", values="case 2 manifolds")
    fig, ax = plt.subplots(figsize=(8.5, 7))
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("blues", ["#E4EDF7", P["blue_main"]])
    vmax = gain.values.max()
    for i, r in enumerate(gain.index):
        for j, m in enumerate(gain.columns):
            v, k = gain.loc[r, m], int(n.loc[r, m])
            face = cmap(0.15 + 0.85 * v / vmax) if k > 1 else "#F2F2F0"
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=face, edgecolor="white", lw=2))
            dark = k > 1 and v / vmax > 0.45
            ax.text(j + 0.5, i + 0.5, f"{v:.0f}", ha="center", va="center", fontsize=11,
                    color="white" if dark else (P["ink"] if k > 1 else P["grey_mid"]))
    j0, i0 = list(gain.columns).index(1), list(gain.index).index(1)
    ax.add_patch(Rectangle((j0, i0), 1, 1, fill=False, edgecolor=P["ink"], lw=2.5))
    ax.text(j0 + 0.5, i0 + 0.15, "base", ha="center", fontsize=9, color=P["ink"])
    ax.set_xlim(0, gain.shape[1]); ax.set_ylim(0, gain.shape[0])
    ax.set_xticks(np.arange(gain.shape[1]) + 0.5, [f"×{c:g}" for c in gain.columns])
    ax.set_yticks(np.arange(gain.shape[0]) + 0.5, [f"×{r:g}" for r in gain.index])
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("Vessel mobilization time multiplier")
    ax.set_ylabel("Manifold failure-rate multiplier")
    ax.legend(handles=[Patch(facecolor="#F2F2F0", label="1 manifold (= CAPEX-only layout)"),
                       Patch(facecolor=cmap(0.6), label="2 manifolds; NPV gain (MUSD)")],
              loc="upper left", bbox_to_anchor=(0, 1.1), ncol=2, fontsize=11)
    finalize_figure(fig, out)


def main(cfg_path):
    apply_publication_style(FigureStyle(font_size=15, axes_linewidth=2))
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    res = results_dir(cfg_path)
    c1 = optimize_capex(field, cfg)
    ra = optimize_npv(field, cfg, risk_weight=1.0, scenarios=sample_scenarios(field, cfg))
    layouts = {"CAPEX-optimal (one 6-slot manifold)": (c1.assignment, c1.sizes),
               "Risk-averse (4-slot + 2-slot manifolds)": (ra.assignment, ra.sizes)}
    fig4_map(field, OUT / "fig4_solveig_map")
    fig5_weather(OUT / "fig5_weather_wait")
    fig6_mc(field, cfg, layouts, OUT / "fig6_mc_distribution")
    fig7_layouts(field, layouts, OUT / "fig7_layouts")
    fig8_tornado(res, OUT / "fig8_tornado")
    fig9_map(res, OUT / "fig9_switching_map")
    print(f"Saved figures to {OUT}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "config" / "solveig_weather.yaml")
