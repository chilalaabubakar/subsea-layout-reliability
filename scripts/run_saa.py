"""Sample-average check of the risk-averse (CVaR) MILP (Kleywegt et al. 2002).

The risk-averse MILP sees the tail of the failure cost through a sample of scenarios, so
its answer depends on the sample. This script measures how much:

1. Reference: every feasible layout is evaluated on one large sample (risk.n_reference
   scenarios). For each risk weight w this gives the layout that is best on that sample.
2. Replications: the MILP is solved for risk.replications independent samples of
   risk.replication_scenarios scenarios. Each answer is scored on the reference sample;
   its regret is its reference cost minus the reference cost of the best layout.
3. Gap estimate: the mean of the replications' optimal costs is a statistical lower bound
   on the true optimal cost; the reference cost of the chosen layout is an upper bound.

4. The best layouts on the reference sample are re-evaluated with the full simulation
   (overlapping outages merged), as in step 7. If step 7 has been run, its risk-sweep
   answers (MILP with risk.n_scenarios scenarios) are scored on the reference sample too.

Usage:  python scripts/run_saa.py [--jobs N] [path/to/config.yaml]
Writes (in results/ or results/<config name>/):
        step7_saa_layouts.csv       every feasible layout: fixed cost, expected failure cost and
                                    CVaR on the reference sample
        step7_saa_reference.csv     best layout on the reference sample by risk weight, with its
                                    full-simulation statistics
        step7_saa_replications.csv  every MILP answer of the replications
        step7_saa_summary.csv       one row per risk weight
        step7_saa_sweep.csv         the step-7 sweep answers scored on the reference (if present)
"""
import argparse
import copy
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from layout_rel.config import DEFAULT_CONFIG, field_path, load_config, param, results_dir
from layout_rel.economics import npv_breakdown, revenue_pv
from layout_rel.layout import load_field
from layout_rel.montecarlo import sample_scenarios, simulate_layout, summary
from layout_rel.optimizer import optimize_npv
from layout_rel.saa import assignment_text, describe, layout_table, reference_sample

M = 1e6
WEIGHTS = (0.25, 0.5, 0.75, 1.0)


def _setup(cfg_path):
    cfg = load_config(cfg_path)
    return cfg, load_field(field_path(cfg), param(cfg, "routing.length_factor"))


def replication(args):
    """Solve the MILP for one scenario sample and every weight; returns plain rows."""
    cfg_path, r = args
    cfg, field = _setup(cfg_path)
    scen = sample_scenarios(field, cfg, n=param(cfg, "risk.replication_scenarios"),
                            seed=param(cfg, "risk.seed") + 1000 + r)
    rev, rows = revenue_pv(field, cfg), []
    for w in WEIGHTS:
        t = time.perf_counter()
        sol = optimize_npv(field, cfg, risk_weight=w, scenarios=scen)
        rows.append({"replication": r, "w": w, "assignment": sol.assignment, "sizes": sol.sizes,
                     "MILP cost [MUSD]": (rev - sol.objective) / M, "solve time [s]": time.perf_counter() - t})
    return rows


def switching_weights(tab) -> list[tuple[float, int]]:
    """(w, layout index) each time the best layout on the reference sample changes, w from 0 to 1."""
    out, w = [(0.0, tab.best(0.0))], 0.0
    for w in np.round(np.arange(0.0, 1.0001, 0.001), 3):
        b = tab.best(float(w))
        if b != out[-1][1]:
            out.append((float(w), b))
    return out


def main(cfg_path, jobs):
    cfg, field = _setup(cfg_path)
    out = results_dir(cfg_path)
    beta, R = param(cfg, "risk.alpha"), int(param(cfg, "risk.replications"))

    t = time.perf_counter()
    ref = reference_sample(field, cfg)
    tab = layout_table(field, cfg, ref)
    print(f"reference: {len(tab.layouts)} layouts on {len(ref)} scenarios ({time.perf_counter() - t:.0f} s)")

    ck = f"CVaR{int(beta * 100)}"
    pd.DataFrame({"layout": [describe(a, s) for a, s in tab.layouts],
                  "assignment": [assignment_text(a) for a, _ in tab.layouts],
                  "fixed cost CAPEX(1+oA) [MUSD]": tab.fixed / M, "expected failure cost [MUSD]": tab.ev / M,
                  f"{ck} of failure cost, linear form [MUSD]": tab.cvar / M}
                 ).to_csv(out / "step7_saa_layouts.csv", index=False, float_format="%.4f")

    mean_wait_cfg = copy.deepcopy(cfg)
    mean_wait_cfg["montecarlo"]["weather_wait_file"]["value"] = None
    sw = switching_weights(tab)
    rows = []
    for (w0, i), nxt in zip(sw, sw[1:] + [(1.0, None)]):
        a, s = tab.layouts[i]
        n = npv_breakdown(field, cfg, a, s)
        st = summary(simulate_layout(field, cfg, a, s).total_pv, beta)      # full simulation
        flat = summary(simulate_layout(field, mean_wait_cfg, a, s).total_pv, beta)
        rows.append({"from w": w0, "to w": nxt[0], "best layout on reference sample": describe(a, s),
                     "assignment": assignment_text(a),
                     "EV NPV [MUSD]": n["npv"] / M, "CAPEX [MUSD]": n["capex"] / M,
                     "fixed cost CAPEX(1+oA) [MUSD]": tab.fixed[i] / M, "expected failure cost [MUSD]": tab.ev[i] / M,
                     f"{ck} of failure cost, linear form [MUSD]": tab.cvar[i] / M,
                     "MC mean failure PV [MUSD]": st["mean"] / M, "MC 95% CI +/- [MUSD]": 1.96 * st["se_mean"] / M,
                     "EV - MC [%]": 100 * (tab.ev[i] / st["mean"] - 1),
                     "MC std [MUSD]": st["std"] / M, "MC P90 [MUSD]": st["p90"] / M,
                     f"MC {ck.upper()} [MUSD]": st[ck.lower()] / M,
                     # same simulation, but every failure waits the mean time (as the EV model assumes)
                     "MC mean, mean wait [MUSD]": flat["mean"] / M, "MC std, mean wait [MUSD]": flat["std"] / M,
                     f"MC {ck.upper()}, mean wait [MUSD]": flat[ck.lower()] / M})
    ref_tab = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print("\nBest layout on the reference sample by risk weight:")
    print(ref_tab.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    t = time.perf_counter()
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        reps = [row for rows_r in ex.map(replication, [(cfg_path, r) for r in range(R)]) for row in rows_r]
    print(f"\n{R} replications x {len(WEIGHTS)} weights solved in {time.perf_counter() - t:.0f} s")

    rep_rows, summ_rows = [], []
    for w in WEIGHTS:
        obj, best = tab.objective(w), tab.best(w)
        mine = [r for r in reps if r["w"] == w]
        idx = [tab.index(r["assignment"], r["sizes"]) for r in mine]
        for r, i in zip(mine, idx):
            rep_rows.append({"w": w, "replication": r["replication"], "MILP layout": describe(r["assignment"], r["sizes"]),
                             "MILP cost [MUSD]": r["MILP cost [MUSD]"], "reference cost [MUSD]": obj[i] / M,
                             "regret on reference [MUSD]": (obj[i] - obj[best]) / M,
                             "solve time [s]": r["solve time [s]"]})
        v = np.array([r["MILP cost [MUSD]"] for r in mine])
        regret = np.array([(obj[i] - obj[best]) / M for i in idx])
        picks = pd.Series([describe(*tab.layouts[i]) for i in idx]).value_counts()
        summ_rows.append({"w": w, "best layout on reference": describe(*tab.layouts[best]),
                        "replications choosing it": int((np.array(idx) == best).sum()), "replications": R,
                        "other layouts chosen": "; ".join(f"{k} x{n}" for k, n in picks.items()
                                                          if k != describe(*tab.layouts[best])) or "-",
                        "mean regret [MUSD]": regret.mean(), "max regret [MUSD]": regret.max(),
                        "lower bound: mean MILP cost [MUSD]": v.mean(),
                        "+/- 95% [MUSD]": 1.96 * v.std(ddof=1) / np.sqrt(R),
                        "upper bound: reference cost of best [MUSD]": obj[best] / M,
                        "gap estimate [MUSD]": obj[best] / M - v.mean()})
    summ = pd.DataFrame(summ_rows)
    print(f"\nMILP with {param(cfg, 'risk.replication_scenarios')} scenarios, scored on the reference sample:")
    print(summ.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    sweep_file = out / "step7_risk_sweep.csv"
    if sweep_file.exists() and "assignment" in pd.read_csv(sweep_file, nrows=1).columns:
        sweep = pd.read_csv(sweep_file)
        rows = []
        for _, r in sweep.iterrows():
            obj, i = tab.objective(r.rho), tab.index_of_text(r.assignment)
            rows.append({"w": r.rho, "MILP layout": r.layout, "best layout on reference": describe(*tab.layouts[tab.best(r.rho)]),
                         "reference cost [MUSD]": obj[i] / M, "regret on reference [MUSD]": (obj[i] - obj.min()) / M,
                         "regret [% of cost]": 100 * (obj[i] / obj.min() - 1)})
        sw_tab = pd.DataFrame(rows)
        print(f"\nStep-7 sweep (MILP with {param(cfg, 'risk.n_scenarios')} scenarios) scored on the reference sample:")
        print(sw_tab.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
        sw_tab.to_csv(out / "step7_saa_sweep.csv", index=False)

    ref_tab.to_csv(out / "step7_saa_reference.csv", index=False)
    pd.DataFrame(rep_rows).to_csv(out / "step7_saa_replications.csv", index=False)
    summ.to_csv(out / "step7_saa_summary.csv", index=False)
    print(f"\nSaved {out / 'step7_saa_summary.csv'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("config", nargs="?", default=str(DEFAULT_CONFIG))
    a = ap.parse_args()
    main(Path(a.config), a.jobs)
