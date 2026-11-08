"""What-if: tie-back umbilical failure rate per installed unit (the model) vs per km.

The model applies the OREDA umbilical rate per installed tie-back umbilical, whatever its
length. OREDA does not give the length of the units behind that rate, so this script
assumes a unit length L_ref (config: umbilical_length_check.ref_lengths) and turns the rate
into rate_per_unit / L_ref per km. Each tie-back then fails in proportion to its length.
For each L_ref it solves case 2 (expected value) and the risk-averse case (w = 1).

Usage:  python scripts/umbilical_length_check.py [path/to/config.yaml]
        (default: config/solveig_weather.yaml)
Writes: results/<case>/umbilical_length_check.csv
"""
import copy
import sys
from pathlib import Path

import pandas as pd

from layout_rel.config import REPO_ROOT, field_path, load_config, param, param_raw, results_dir
from layout_rel.economics import npv_breakdown
from layout_rel.layout import load_field
from layout_rel.montecarlo import sample_scenarios
from layout_rel.optimizer import optimize_npv
from layout_rel.units import YEAR

M = 1e6


def per_km_config(cfg: dict, ref_km: float) -> dict:
    """Copy of ``cfg`` with the tie-back umbilical rate spread over ``ref_km`` of line."""
    c = copy.deepcopy(cfg)
    per_year = param(cfg, "reliability.tieback_umbilical.failure_rate_per_unit") * YEAR
    node = c["reliability"]["tieback_umbilical"]
    del node["failure_rate_per_unit"]
    node["failure_rate_per_km"] = {
        "value": per_year / ref_km, "unit": "1/(km*yr)",
        "source": f"What-if: OREDA per-unit rate over an assumed {ref_km:g} km unit length."}
    return c


def solve(field, cfg, label: str) -> list[dict]:
    rows = []
    for w in (0.0, 1.0):
        kw = {"risk_weight": w, "scenarios": sample_scenarios(field, cfg)} if w else {}
        r = optimize_npv(field, cfg, **kw)
        b = npv_breakdown(field, cfg, r.assignment, r.sizes)
        rows.append({"umbilical rate": label, "risk weight w": w,
                     "layout": " + ".join(f"{s}({k}-slot)" for s, k in sorted(r.sizes.items())),
                     "NPV [MUSD]": b["npv"] / M,
                     "failure PV [MUSD]": (b["repair_cost"] + b["lost_production"]) / M})
    return rows


def main(cfg_path: Path) -> None:
    cfg = load_config(cfg_path)
    field = load_field(field_path(cfg), param(cfg, "routing.length_factor"))
    rows = solve(field, cfg, "per unit (model)")
    for ref_km in param_raw(cfg, "umbilical_length_check.ref_lengths"):
        rate_km = param(cfg, "reliability.tieback_umbilical.failure_rate_per_unit") * YEAR / ref_km
        rows += solve(field, per_km_config(cfg, ref_km),
                      f"per km, {rate_km:.4f} /km-yr (unit length {ref_km:g} km)")
    out = results_dir(cfg_path) / "umbilical_length_check.csv"
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    print(df.round(1).to_string(index=False))
    print(f"Saved {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "config" / "solveig_weather.yaml")
