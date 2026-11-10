"""Spread of the reliability gain on synthetic fields: several fields per size, and the
variants of the manifold-rate model (config scaling_study.spread_variants).

For every size, seed and variant: case 1 and case 2 are solved, and the NPV gain of the
case 2 layout over the case 1 layout is recorded (both evaluated under that variant).

Usage:  python scripts/run_scaling_spread.py [--jobs N] [path/to/config.yaml]
Writes: results/<case>/step9_scaling_spread.csv (every run), step9_scaling_spread_summary.csv
"""
import argparse
import copy
import math
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from layout_rel.config import REPO_ROOT, load_config, param, param_raw, results_dir
from layout_rel.economics import npv_breakdown
from layout_rel.optimizer import build_capex_model, build_npv_model, solve
from layout_rel.synthetic import synthetic_field
from layout_rel.units import KM

M = 1e6


def run(args) -> dict:
    cfg_path, n_wells, n_sites, seed, name, changes = args
    cfg = copy.deepcopy(load_config(cfg_path))
    g = lambda k: param_raw(cfg, f"scaling_study.{k}")
    for key, value in changes.items():
        node = cfg
        for part in key.split("."):
            node = node[part]
        node["value"] = value
    field = synthetic_field(n_wells, n_sites, math.sqrt(n_wells / g("well_density")) * KM, g("host_distance") * KM,
                            seed, param(cfg, "routing.length_factor"))
    c1 = solve(build_capex_model(field, cfg), cfg, time_limit=g("time_limit"))
    t = time.perf_counter()
    c2 = solve(build_npv_model(field, cfg, risk_weight=0.0), cfg, time_limit=g("time_limit"))
    t2 = time.perf_counter() - t
    n1, n2 = npv_breakdown(field, cfg, c1.assignment, c1.sizes), npv_breakdown(field, cfg, c2.assignment, c2.sizes)
    slots = lambda s: " + ".join(str(v) for v in sorted(s.sizes.values(), reverse=True))
    return {"wells": n_wells, "candidate sites": n_sites, "seed": seed, "variant": name,
            "case 1 manifold slots": slots(c1), "case 2 manifold slots": slots(c2),
            "layout differs": c1.assignment != c2.assignment or c1.sizes != c2.sizes,
            "NPV gain [MUSD]": (n2["npv"] - n1["npv"]) / M, "extra CAPEX [MUSD]": (n2["capex"] - n1["capex"]) / M,
            "case 2 time [s]": t2, "case 2 gap [%]": 100 * c2.info["gap"]}


def main(cfg_path: Path, jobs: int) -> None:
    cfg = load_config(cfg_path)
    g = lambda k: param_raw(cfg, f"scaling_study.{k}")
    jobs_list = [(cfg_path, w, s, g("seed") + r, name, ch) for w, s in g("spread_instances")
                 for r in range(g("replicates")) for name, ch in g("spread_variants").items()]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        df = pd.DataFrame(list(ex.map(run, jobs_list)))
    out = results_dir(cfg_path)
    df.to_csv(out / "step9_scaling_spread.csv", index=False)
    summ = df.groupby(["wells", "variant"], sort=False).agg(
        fields=("seed", "count"), differ=("layout differs", "sum"), gain_min=("NPV gain [MUSD]", "min"),
        gain_median=("NPV gain [MUSD]", "median"), gain_max=("NPV gain [MUSD]", "max"),
        not_proven=("case 2 gap [%]", lambda x: int((x > 0.01).sum())), time_max=("case 2 time [s]", "max")).reset_index()
    summ.to_csv(out / "step9_scaling_spread_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(summ.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("config", nargs="?", default=str(REPO_ROOT / "config" / "solveig_weather.yaml"))
    a = ap.parse_args()
    main(Path(a.config), a.jobs)
