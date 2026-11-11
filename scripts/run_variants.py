"""Case 1 against case 2 for one field under the variants of the manifold-rate model and of
deferred production (config scaling_study.spread_variants and assumption_checks.cases).

For fields too large to rank every layout (scripts/run_assumptions.py needs that), this gives
the expected-value result of each variant: do the two cases differ, and by how much.

Usage:  python scripts/run_variants.py path/to/config.yaml
Writes: results/<case>/step8_variants.csv
"""
import copy
import sys
from pathlib import Path

import pandas as pd

from layout_rel.config import field_path, load_config, param, param_raw, results_dir
from layout_rel.economics import npv_breakdown
from layout_rel.layout import load_field
from layout_rel.optimizer import optimize_capex, optimize_npv

M = 1e6


def main(cfg_path: Path) -> None:
    base = load_config(cfg_path)
    field = load_field(field_path(base), param(base, "routing.length_factor"))
    variants = {**param_raw(base, "scaling_study.spread_variants"),
                **{k: v for k, v in param_raw(base, "assumption_checks.cases").items() if k.startswith("deferred")}}
    slots = lambda s: " + ".join(f"{k}-slot at {site}" for site, k in sorted(s.sizes.items()))
    rows = []
    for name, changes in variants.items():
        cfg = copy.deepcopy(base)
        for key, value in changes.items():
            node = cfg
            for part in key.split("."):
                node = node[part]
            node["value"] = value
        c1, c2 = optimize_capex(field, cfg), optimize_npv(field, cfg)
        n1, n2 = npv_breakdown(field, cfg, c1.assignment, c1.sizes), npv_breakdown(field, cfg, c2.assignment, c2.sizes)
        rows.append({"variant": name, "case 1 layout": slots(c1), "case 2 layout": slots(c2),
                     "layout differs": c1.assignment != c2.assignment or c1.sizes != c2.sizes,
                     "failure PV case-1 layout [MUSD]": (n1["repair_cost"] + n1["lost_production"]) / M,
                     "failure PV case 2 [MUSD]": (n2["repair_cost"] + n2["lost_production"]) / M,
                     "NPV case 2 [MUSD]": n2["npv"] / M, "NPV gain [MUSD]": (n2["npv"] - n1["npv"]) / M,
                     "extra CAPEX [MUSD]": (n2["capex"] - n1["capex"]) / M})
    df = pd.DataFrame(rows)
    out = results_dir(cfg_path) / "step8_variants.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    print(f"Saved {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
