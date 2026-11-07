"""Waiting-on-weather for each repair type at the Solveig location (NORA3 hindcast).

For each repair kind (tree, manifold, flowline, umbilical), following DNV-ST-N001 (2023):
the active repair (config `maintenance.<kind>.repair_days`) is split into weather-restricted
phases of at most `weather.max_phase` hours; each phase needs a window of T_R = 2 T_POP hours
with Hs <= alpha x OP_LIM (OP_LIM = vessel Hs limit, alpha from `weather.alpha_table`).

Usage:  python scripts/weather_windows.py [config] [hs.csv]
        defaults: config/solveig_case.yaml, data/raw/metno/nora3_hs_solveig.csv
Writes: results/weather_solveig_monthly.csv, results/weather_solveig.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from layout_rel.config import CONFIG_DIR, REPO_ROOT, load_config, param_raw
from layout_rel.plotting import C_GRID, C_HOST, C_INK, C_INK_2, C_MANIFOLD, C_WELL
from layout_rel.weather import alpha_factor, phase_plan, phased_waiting_hours

WINTER, SUMMER = (10, 11, 12, 1, 2, 3), (4, 5, 6, 7, 8, 9)
KINDS = ("xmas_tree", "manifold", "flowline", "umbilical")


def main(cfg_path, hs_path):
    cfg = load_config(cfg_path)
    hs = pd.read_csv(hs_path, parse_dates=["time"]).set_index("time")["hs_m"].sort_index()
    hs = hs[~hs.index.duplicated()]
    years = f"{hs.index.min():%Y-%m}..{hs.index.max():%Y-%m}"
    print(f"NORA3 Hs at Solveig, {years}: {len(hs)} hours, mean {hs.mean():.2f} m, "
          f"P90 {hs.quantile(0.9):.2f} m")

    table = param_raw(cfg, "weather.alpha_table")
    max_phase = param_raw(cfg, "weather.max_phase")
    cont = param_raw(cfg, "weather.contingency_factor")
    min_c = param_raw(cfg, "weather.min_contingency")
    month = hs.index.month
    rows, monthly = [], []
    for kind in KINDS:
        vessel = param_raw(cfg, f"maintenance.{kind}.vessel")
        op_lim = param_raw(cfg, f"weather.{vessel}_hs_limit")
        repair_h = param_raw(cfg, f"maintenance.{kind}.repair_days") * 24
        phases = phase_plan(repair_h, max_phase)
        w = pd.Series(phased_waiting_hours(hs.to_numpy(), op_lim, repair_h, table, max_phase,
                                           cont, min_c), index=hs.index)
        a = alpha_factor(table, phases[0], op_lim)
        g = w.groupby(month)
        monthly.append(pd.DataFrame({"mean_wait_h": g.mean(), "p90_wait_h": g.quantile(0.9),
                                     "kind": kind}))
        rows.append({"repair": kind, "vessel": vessel, "OP_LIM Hs [m]": op_lim,
                     "phases x T_POP [h]": f"{len(phases)} x {phases[0]:.0f}",
                     "alpha": a, "OP_WF Hs [m]": a * op_lim,
                     "mean wait, all year [d]": w.mean() / 24,
                     "mean wait, winter Oct-Mar [d]": w[month.isin(WINTER)].mean() / 24,
                     "mean wait, summer Apr-Sep [d]": w[month.isin(SUMMER)].mean() / 24,
                     "P90 wait, all year [d]": w.quantile(0.9) / 24})
    tab = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print(tab.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    mon = pd.concat(monthly).rename_axis("month").reset_index()
    out = REPO_ROOT / "results"
    mon.to_csv(out / "weather_solveig_monthly.csv", index=False)
    tab.to_csv(out / "weather_solveig_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 5))
    for kind, col in zip(KINDS, (C_WELL, C_MANIFOLD, C_HOST, C_INK_2)):
        d = mon[mon.kind == kind]
        r = tab.loc[tab.repair == kind].iloc[0]
        ax.plot(d.month, d.mean_wait_h / 24, marker="o", ms=6, lw=2, color=col,
                label=f"{kind}: {r['phases x T_POP [h]']} h, Hs <= {r['OP_WF Hs [m]']:.2f} m")
    ax.set_xticks(range(1, 13), ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.set_ylabel("Mean wait for a weather window [days]", color=C_INK_2)
    ax.set_title(f"Waiting on weather at Solveig by month (NORA3 hindcast {years})",
                 loc="left", color=C_INK, fontsize=11)
    ax.legend(frameon=False, labelcolor=C_INK_2, fontsize=9)
    ax.grid(True, color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=C_INK_2)
    for sp in ax.spines.values():
        sp.set_color(C_GRID)
    fig.tight_layout()
    fig.savefig(out / "weather_solveig.png", dpi=200)
    print(f"Saved {out / 'weather_solveig.png'}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]) if a else CONFIG_DIR / "solveig_case.yaml",
         Path(a[1]) if len(a) > 1 else REPO_ROOT / "data" / "raw" / "metno" / "nora3_hs_solveig.csv")
