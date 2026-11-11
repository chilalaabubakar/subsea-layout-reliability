"""Waiting-on-weather for each repair type at Solveig (NORA3 hindcast, DNV-ST-N001 method).

For each repair kind (tree, manifold, flowline, umbilical) the weather-critical part of the repair
is split into weather-restricted phases; each phase needs a window of T_R = (1 + c) T_POP hours
(T_C >= 6 h) with Hs <= alpha x OP_LIM (OP_LIM = vessel Hs limit, alpha from `weather.alpha_table`).

  mode 'lifts' (base):  weather_critical_lifts x lift_duration, one phase per lift
  mode 'whole' (upper): the whole active repair (repair_days), phases <= weather.max_phase

Start hours are the hours of hs.csv (2014-2023). A repair whose vessel is ready late in
2023 needs weather after the end of that record, so the series is extended with a run-out
file (2024). Run-out hours only complete windows; they are never start hours. Without the
run-out the last weeks of December 2023 would drop out of the mean, which biases it low.

Usage:  python scripts/weather_windows.py [config] [hs.csv] [runout.csv] [case name]
        defaults: config/solveig_case.yaml, data/raw/metno/nora3_hs_solveig.csv,
                  data/raw/metno/nora3_hs_solveig_2024.csv
Writes: results/weather_solveig_summary.csv, results/weather_solveig_monthly.csv,
        results/weather_solveig.png,
        data/processed/weather_wait_hourly_solveig.csv (base mode: wait in hours for every
        start hour and repair kind; the Monte Carlo model samples from it),
        and GENERATED case configs
        config/solveig_weather.yaml (year-round mean wait, base mode),
        config/solveig_weather_winter.yaml, config/solveig_weather_summer.yaml,
        config/solveig_weather_whole.yaml (upper bound: whole repair weather-critical).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from layout_rel.config import CONFIG_DIR, REPO_ROOT, load_config, param_raw
from layout_rel.plotting import C_GRID, C_INK, C_INK_2, C_MANIFOLD, C_WELL
from layout_rel.weather import alpha_factor, phase_plan, phased_waiting_hours

WINTER, SUMMER = (10, 11, 12, 1, 2, 3), (4, 5, 6, 7, 8, 9)
KINDS = ("xmas_tree", "manifold", "flowline", "umbilical")
SEASONS = {"year": tuple(range(1, 13)), "winter": WINTER, "summer": SUMMER}


def critical_plan(cfg, kind, mode):
    """(weather-critical hours, max phase length) for a repair kind."""
    if mode == "lifts":
        d = param_raw(cfg, "weather.lift_duration")
        return param_raw(cfg, f"maintenance.{kind}.weather_critical_lifts") * d, d
    return param_raw(cfg, f"maintenance.{kind}.repair_days") * 24, param_raw(cfg, "weather.max_phase")


def waits(cfg, hs, kind, mode) -> pd.Series:
    vessel = param_raw(cfg, f"maintenance.{kind}.vessel")
    hours, phase = critical_plan(cfg, kind, mode)
    w = phased_waiting_hours(hs.to_numpy(), param_raw(cfg, f"weather.{vessel}_hs_limit"), hours,
                             param_raw(cfg, "weather.alpha_table"), phase,
                             param_raw(cfg, "weather.contingency_factor"),
                             param_raw(cfg, "weather.min_contingency"))
    return pd.Series(w, index=hs.index)


NAME = "solveig"          # case name: prefix of the outputs (set from the command line)


def hourly_file() -> Path:
    return Path("data") / "processed" / f"weather_wait_hourly_{NAME}.csv"


def read_hs(path) -> pd.Series:
    hs = pd.read_csv(path, parse_dates=["time"]).set_index("time")["hs_m"].sort_index()
    return hs[~hs.index.duplicated()]


def write_case(name, base_cfg_file, wait_days, mode, season, years, note, hourly=False):
    case = {"_extends": base_cfg_file,
            "maintenance": {"weather_allowance": {
                "value": 0.0, "unit": "fraction of active repair time",
                "source": "0 here: waiting on weather is modelled explicitly from the NORA3 hindcast (weather_wait_days)."}},
            # the 20-30 % allowance is replaced by explicit waits here, so it is not a sensitivity input
            "sensitivity": {"weather_allowance": None}}
    for kind, d in wait_days.items():
        case["maintenance"][kind] = {"weather_wait_days": {
            "value": round(float(d), 2), "unit": "days (expected wait for a weather window, added to downtime)",
            "source": (f"Computed by scripts/weather_windows.py: NORA3 Hs at {NAME.capitalize()} {years}, mode '{mode}', "
                       f"{season} start times; DNV-ST-N001 (2023) Table 2-4 alpha, T_R = 2 T_POP, T_C >= 6 h.")}}
    if hourly:      # the simulation draws each failure's wait from the hourly series (same mean)
        case["montecarlo"] = {"weather_wait_file": {
            "value": hourly_file().as_posix(),
            "unit": "- (CSV with the weather wait in hours for every hindcast hour, columns <repair kind>_h)",
            "source": (f"Written by scripts/weather_windows.py: wait for a weather window if the vessel is ready "
                       f"at that hour, NORA3 Hs at {NAME.capitalize()} {years}, mode '{mode}'.")}}
    path = CONFIG_DIR / name
    with path.open("w") as fh:
        fh.write(f"# GENERATED by scripts/weather_windows.py - do not edit by hand.\n# {note}\n")
        yaml.safe_dump(case, fh, sort_keys=False)
    return path


def main(cfg_path, hs_path, runout_path=None):
    cfg = load_config(cfg_path)
    hs = read_hs(hs_path)
    full = hs
    if runout_path is not None and Path(runout_path).exists():
        run = read_hs(runout_path)
        full = pd.concat([hs, run[run.index > hs.index.max()]])
        if not (full.index[1:] - full.index[:-1] == pd.Timedelta(hours=1)).all():
            raise ValueError("the Hs series with its run-out is not one unbroken hourly series")
        print(f"run-out: {len(full) - len(hs)} hours after {hs.index.max():%Y-%m-%d} (to complete late windows)")
    years = f"{hs.index.min():%Y-%m}..{hs.index.max():%Y-%m}"
    month = hs.index.month
    print(f"NORA3 Hs at {NAME.capitalize()}, {years}: {len(hs)} hours, mean {hs.mean():.2f} m, P90 {hs.quantile(0.9):.2f} m, "
          f"share Hs < 2.0 / 2.5 m: {(hs < 2).mean():.2f} / {(hs < 2.5).mean():.2f}")
    base_mode = param_raw(cfg, "weather.critical_mode")
    table = param_raw(cfg, "weather.alpha_table")

    rows, monthly, mean, hourly = [], [], {}, {}
    for mode in ("lifts", "whole"):
        for kind in KINDS:
            w = waits(cfg, full, kind, mode).loc[hs.index]      # start hours only
            if mode == base_mode:
                hourly[f"{kind}_h"] = w
            vessel = param_raw(cfg, f"maintenance.{kind}.vessel")
            op = param_raw(cfg, f"weather.{vessel}_hs_limit")
            hours, phase = critical_plan(cfg, kind, mode)
            ph = phase_plan(hours, phase)
            row = {"mode": mode, "repair": kind, "vessel": vessel, "OP_LIM [m]": op,
                   "phases x T_POP [h]": f"{len(ph)} x {ph[0]:.0f}",
                   "OP_WF [m]": alpha_factor(table, ph[0], op) * op,
                   "start hours without a window": int(w.isna().sum())}
            for season, months in SEASONS.items():
                d = w[month.isin(months)].mean() / 24
                row[f"mean wait {season} [d]"] = d
                mean[mode, season, kind] = d
            row["P90 wait year [d]"] = w.quantile(0.9) / 24
            rows.append(row)
            g = w.groupby(month)
            monthly.append(pd.DataFrame({"mode": mode, "repair": kind, "mean_wait_d": g.mean() / 24,
                                         "p90_wait_d": g.quantile(0.9) / 24}))
    tab = pd.DataFrame(rows)
    pd.set_option("display.width", 230)
    print(tab.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    out = REPO_ROOT / "results"
    tab.to_csv(out / f"weather_{NAME}_summary.csv", index=False)
    mon = pd.concat(monthly).rename_axis("month").reset_index()
    mon.to_csv(out / f"weather_{NAME}_monthly.csv", index=False)
    hw = pd.DataFrame(hourly)
    if hw.isna().any().any():
        raise ValueError("some start hours have no complete weather window: extend the run-out file")
    (REPO_ROOT / hourly_file()).parent.mkdir(parents=True, exist_ok=True)
    hw.round().astype(int).rename_axis("time").to_csv(REPO_ROOT / hourly_file())
    print(f"wrote {hourly_file()}")

    # figure: monthly mean wait, base mode, light vs heavy vessel repairs
    fig, ax = plt.subplots(figsize=(9, 5))
    for kind, col in (("xmas_tree", C_WELL), ("manifold", C_MANIFOLD)):
        d = mon[(mon["mode"] == base_mode) & (mon.repair == kind)]
        r = tab[(tab["mode"] == base_mode) & (tab.repair == kind)].iloc[0]
        lab = ("tree (light vessel)" if kind == "xmas_tree" else "manifold, flowline, umbilical (heavy vessel)")
        ax.plot(d.month, d.mean_wait_d, marker="o", ms=7, lw=2, color=col,
                label=f"{lab}: {r['phases x T_POP [h]']} h lift(s), $H_s$ \u2264 {r['OP_WF [m]']:.2f} m")
    ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                 "Nov", "Dec"])
    ax.set_ylabel("Mean wait for a weather window [days]", color=C_INK_2)
    ax.set_title(f"Waiting on weather at {NAME.capitalize()} by month the vessel is ready (NORA3 {years}, DNV-ST-N001)",
                 loc="left", color=C_INK, fontsize=11)
    ax.legend(frameon=False, labelcolor=C_INK_2, fontsize=9)
    ax.grid(True, color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=C_INK_2)
    for sp in ax.spines.values():
        sp.set_color(C_GRID)
    fig.tight_layout()
    fig.savefig(out / f"weather_{NAME}.png", dpi=200)

    base = Path(cfg_path).name
    for name, mode, season, note in (
            (f"{NAME}_weather.yaml", base_mode, "year", "North Sea case with year-round mean waiting on weather (base)."),
            (f"{NAME}_weather_winter.yaml", base_mode, "winter", "Bound: every repair vessel is ready in winter (Oct-Mar)."),
            (f"{NAME}_weather_summer.yaml", base_mode, "summer", "Bound: every repair vessel is ready in summer (Apr-Sep)."),
            (f"{NAME}_weather_whole.yaml", "whole", "year", "Upper bound: whole active repair is weather-critical.")):
        p = write_case(name, base, {k: mean[mode, season, k] for k in KINDS}, mode, season, years, note,
                       hourly=(mode == base_mode and season == "year"))
        print(f"wrote {p.relative_to(REPO_ROOT)}")
    print(f"Saved {out / f'weather_{NAME}.png'}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) > 3:                      # optional fourth argument: case name (default solveig)
        NAME = a[3]
    main(Path(a[0]) if a else CONFIG_DIR / "solveig_case.yaml",
         Path(a[1]) if len(a) > 1 else REPO_ROOT / "data" / "raw" / "metno" / "nora3_hs_solveig.csv",
         Path(a[2]) if len(a) > 2 else REPO_ROOT / "data" / "raw" / "metno" / "nora3_hs_solveig_2024.csv")
