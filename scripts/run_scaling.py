"""Scaling study: size and solve time of the MILPs on larger synthetic fields.

For each instance of config scaling_study.instances (wells, candidate sites) a field is
drawn (layout_rel.synthetic), and three MILPs are solved with the data of the given config:
case 1 (CAPEX only), case 2 (expected NPV) and the risk-averse model. Each solve gets
scaling_study.time_limit seconds; if that runs out, the best layout found and its gap to
the solver's bound are reported.

Usage:  python scripts/run_scaling.py [--jobs N] [path/to/config.yaml]
        (default: config/solveig_weather.yaml)
Writes: results/<case>/step9_scaling.csv
"""
import argparse
import math
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from layout_rel.config import REPO_ROOT, load_config, param, param_raw, results_dir
from layout_rel.economics import manifold_sizes, npv_breakdown
from layout_rel.montecarlo import sample_scenarios
from layout_rel.optimizer import build_capex_model, build_npv_model, solve
from layout_rel.synthetic import synthetic_field
from layout_rel.units import KM

M = 1e6


def timed(build, cfg, limit):
    t = time.perf_counter()
    m = build()
    t_build = time.perf_counter() - t
    t = time.perf_counter()
    sol = solve(m, cfg, time_limit=limit)
    return sol, t_build, time.perf_counter() - t


def run(args) -> dict:
    cfg_path, n_wells, n_sites = args
    cfg = load_config(cfg_path)
    g = lambda k: param_raw(cfg, f"scaling_study.{k}")
    side = math.sqrt(n_wells / g("well_density")) * KM
    field = synthetic_field(n_wells, n_sites, side, g("host_distance") * KM, g("seed"),
                            param(cfg, "routing.length_factor"))
    limit, k = g("time_limit"), len(manifold_sizes(cfg))
    c1, _, t1 = timed(lambda: build_capex_model(field, cfg), cfg, limit)
    c2, _, t2 = timed(lambda: build_npv_model(field, cfg, risk_weight=0.0), cfg, limit)
    scen = sample_scenarios(field, cfg, n=g("n_scenarios"))
    ra, tb, t3 = timed(lambda: build_npv_model(field, cfg, risk_weight=g("risk_weight"), scenarios=scen), cfg, limit)
    n1 = npv_breakdown(field, cfg, c1.assignment, c1.sizes)
    n2 = npv_breakdown(field, cfg, c2.assignment, c2.sizes)
    sizes = lambda s: " + ".join(str(v) for v in sorted(s.sizes.values(), reverse=True))
    return {"wells": n_wells, "candidate sites": n_sites, "side of square [km]": side / KM,
            "binary variables": n_sites * k + n_wells * n_sites, "continuous variables (z)": n_wells * n_sites * k,
            "case 1 time [s]": t1, "case 1 manifold slots": sizes(c1),
            "case 2 time [s]": t2, "case 2 gap [%]": 100 * c2.info["gap"], "case 2 manifold slots": sizes(c2),
            "NPV gain of case 2 over case-1 layout [MUSD]": (n2["npv"] - n1["npv"]) / M,
            "failure PV case-1 layout [MUSD]": (n1["repair_cost"] + n1["lost_production"]) / M,
            "failure PV case 2 [MUSD]": (n2["repair_cost"] + n2["lost_production"]) / M,
            "CAPEX case-1 layout [MUSD]": n1["capex"] / M, "CAPEX case 2 [MUSD]": n2["capex"] / M,
            "risk-averse build time [s]": tb, "risk-averse time [s]": t3, "risk-averse gap [%]": 100 * ra.info["gap"],
            "risk-averse manifold slots": sizes(ra)}


def main(cfg_path: Path, jobs: int) -> None:
    cfg = load_config(cfg_path)
    inst = param_raw(cfg, "scaling_study.instances")
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        rows = list(ex.map(run, [(cfg_path, w, s) for w, s in inst]))
    df = pd.DataFrame(rows)
    out = results_dir(cfg_path) / "step9_scaling.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    print(df.T.to_string(float_format=lambda v: f"{v:,.2f}"))
    print(f"Saved {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("config", nargs="?", default=str(REPO_ROOT / "config" / "solveig_weather.yaml"))
    a = ap.parse_args()
    main(Path(a.config), a.jobs)
