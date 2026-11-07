"""Step 5: expected yearly failure cost of candidate layouts (plateau, undiscounted).

Compares the CAPEX-only optimum with hand-picked alternatives, to preview the
research question before the failure cost goes into the optimizer (step 6).

Usage:  python scripts/run_failure_cost.py [path/to/config.yaml]
Writes: results/step5_failure_cost.csv, results/step5_failure_cost_by_kind.csv
"""
import sys
from pathlib import Path

import pandas as pd

from layout_rel.config import DEFAULT_CONFIG, REPO_ROOT, field_path, load_config, param, placeholders
from layout_rel.economics import capex_breakdown
from layout_rel.layout import load_field
from layout_rel.maintenance import expected_failure_cost, repair
from layout_rel.optimizer import optimize_capex
from layout_rel.units import DAY, YEAR

M = 1e6


def main(cfg_path=DEFAULT_CONFIG):
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    case1 = optimize_capex(field, cfg)
    layouts = {
        "case 1 optimum": case1.assignment,
        "M1 + M3 (3+3)": {"W1": "M1", "W2": "M1", "W3": "M1", "W4": "M3", "W5": "M3", "W6": "M3"},
        "M1 + M2 + M3 (2+2+2)": {"W1": "M1", "W2": "M1", "W3": "M2", "W4": "M2", "W5": "M3", "W6": "M3"},
    }

    print("Repair events (downtime incl. mobilisation and weather; cost incl. vessel and spare):")
    for kind in ("xmas_tree", "manifold", "flowline", "umbilical"):
        r = repair(cfg, kind)
        print(f"  {kind:10s} downtime {r.downtime / DAY:5.1f} d   cost {r.cost / M:5.2f} MUSD")

    rows, kinds = [], []
    for name, a in layouts.items():
        f = expected_failure_cost(field, cfg, a)
        capex = capex_breakdown(field, cfg, a)["total"]
        rows.append({
            "layout": name,
            "manifolds": len(set(a.values())),
            "CAPEX [MUSD]": capex / M,
            "failures [1/yr]": f.failures,
            "repair [MUSD/yr]": f.repair_cost / M,
            "lost prod. [MUSD/yr]": f.lost_production / M,
            "failure cost [MUSD/yr]": f.total / M,
            "downtime/well [d/yr]": sum(f.downtime_per_well.values()) / len(field.wells) / DAY,
        })
        for k, v in f.by_kind.items():
            kinds.append({"layout": name, "component": k, "failures [1/yr]": v["failures"],
                          "repair [MUSD/yr]": v["repair_cost"] / M,
                          "lost prod. [MUSD/yr]": v["lost_production"] / M})
    df, dk = pd.DataFrame(rows), pd.DataFrame(kinds)
    base = df.iloc[0]
    df["extra CAPEX vs case 1 [MUSD]"] = df["CAPEX [MUSD]"] - base["CAPEX [MUSD]"]
    df["failure saving vs case 1 [MUSD/yr]"] = base["failure cost [MUSD/yr]"] - df["failure cost [MUSD/yr]"]

    pd.set_option("display.width", 200)
    print("\nExpected yearly failure cost (plateau production, undiscounted):")
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    print("\nBy component:")
    print(dk.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    out = REPO_ROOT / "results"
    df.to_csv(out / "step5_failure_cost.csv", index=False)
    dk.to_csv(out / "step5_failure_cost_by_kind.csv", index=False)
    todo = placeholders(cfg)
    if todo:
        print(f"\nNOTE: placeholders still in use: {', '.join(todo)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG)
