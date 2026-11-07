"""Cases 2-3: NPV-optimal layout including expected failure costs, compared with case 1.

Also scans vessel mobilisation time and manifold failure rate to find where the
optimal layout changes (a preview of the sensitivity study, step 8).

Usage:  python scripts/run_case2.py [path/to/config.yaml]
Writes: results/case2_layouts.png, results/case2_npv.csv, results/case2_scan.csv
"""
import copy
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from layout_rel.config import DEFAULT_CONFIG, field_path, load_config, param, placeholders, results_dir
from layout_rel.economics import npv_breakdown
from layout_rel.layout import load_field
from layout_rel.maintenance import expected_failure_cost
from layout_rel.optimizer import optimize_capex, optimize_npv
from layout_rel.plotting import plot_layout
from layout_rel.units import DAY

M = 1e6


def describe(sol):
    return " + ".join(f"{s}({sol.sizes[s]}-slot: {sum(1 for t in sol.assignment.values() if t == s)} wells)"
                      for s in sol.open_sites)


def compare(field, cfg):
    c1, c2 = optimize_capex(field, cfg), optimize_npv(field, cfg)
    n1 = npv_breakdown(field, cfg, c1.assignment, c1.sizes)
    n2 = npv_breakdown(field, cfg, c2.assignment, c2.sizes)
    return c1, c2, n1, n2


def scan(field, cfg, label, setter, values):
    rows = []
    for v in values:
        c = copy.deepcopy(cfg)
        setter(c, v)
        c1, c2, n1, n2 = compare(field, c)
        rows.append({"parameter": label, "value": v, "case 2 manifolds": len(c2.open_sites),
                     "case 2 layout": describe(c2),
                     "NPV gain vs case-1 layout [MUSD]": (n2["npv"] - n1["npv"]) / M})
    return rows


def main(cfg_path=DEFAULT_CONFIG):
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    c1, c2, n1, n2 = compare(field, cfg)

    print(f"Case 1 (min CAPEX):          {describe(c1)}")
    print(f"Case 2 (max NPV incl. fail): {describe(c2)}")
    print("Layout changed." if c1.assignment != c2.assignment or c1.sizes != c2.sizes
          else "Layout unchanged.")

    rows = []
    for name, sol, n in (("case 1 layout", c1, n1), ("case 2 layout", c2, n2)):
        f = expected_failure_cost(field, cfg, sol.assignment, sol.sizes)
        rows.append({"layout": name, "description": describe(sol),
                     **{f"{k} [MUSD]": v / M for k, v in n.items()},
                     "failures [1/yr]": f.failures,
                     "downtime/well [d/yr]": sum(f.downtime_per_well.values()) / len(field.wells) / DAY,
                     "lost volume [% of plateau]": 100 * f.lost_volume
                     / (len(field.wells) * param(cfg, "production.well_rate") * 365.25 * DAY)})
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print("\nNPV breakdown (present values):")
    print(df.drop(columns="description").to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # where does the answer change?
    def set_mob(c, x):
        for v in ("msv", "hlv"):
            c["vessels"][f"{v}_mobilisation"]["value"] *= x

    def set_rate(c, x):
        c["reliability"]["manifold"]["failure_rate_per_h"]["value"] *= x

    sc = pd.DataFrame(
        scan(field, cfg, "mobilisation time x", set_mob, [0.5, 1, 1.5, 2, 3, 4])
        + scan(field, cfg, "manifold failure rate x", set_rate, [0.5, 1, 2, 3, 4]))
    print("\nWhere does the optimal layout change? (one parameter at a time)")
    print(sc.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    out = results_dir(cfg_path)
    df.to_csv(out / "case2_npv.csv", index=False)
    sc.to_csv(out / "case2_scan.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    plot_layout(field, c1.assignment, sizes=c1.sizes, ax=axes[0],
                title=f"Case 1 - min CAPEX\nNPV {n1['npv'] / M:,.0f} MUSD, CAPEX {n1['capex'] / M:,.0f} MUSD")
    plot_layout(field, c2.assignment, sizes=c2.sizes, ax=axes[1],
                title=f"Case 2 - max NPV incl. failures\nNPV {n2['npv'] / M:,.0f} MUSD, CAPEX {n2['capex'] / M:,.0f} MUSD")
    axes[0].get_legend().remove()
    fig.tight_layout()
    fig.savefig(out / "case2_layouts.png", dpi=200)
    print(f"\nSaved {out / 'case2_layouts.png'}")
    todo = placeholders(cfg)
    if todo:
        print(f"NOTE: placeholders still in use: {', '.join(todo)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG)
