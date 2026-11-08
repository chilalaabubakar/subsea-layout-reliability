"""Sensitivity analysis: does the optimal layout change, and how much is NPV affected?

Ranges live in the config section `sensitivity` (with sources). For each item and each
level (low, high) the config is copied and changed, then case 1 (min CAPEX) and case 2
(max NPV incl. expected failure cost) are solved again.

Reported per run:
- NPV of the case-2 optimum, and its change from the base case (tornado plot);
- whether the case-2 layout differs from the case-1 layout;
- value of reliability-aware design = NPV(case-2 layout) - NPV(case-1 layout), both
  evaluated with the changed inputs (>= 0 by construction).
"""
from __future__ import annotations

import copy
from typing import Any, Callable

import pandas as pd

from .config import param, param_raw
from .economics import npv_breakdown
from .layout import Field
from .optimizer import optimize_capex, optimize_npv

M = 1e6


def _node(cfg: dict, key: str) -> dict:
    node: Any = cfg
    for part in key.split("."):
        node = node[part]
    return node


def apply(cfg: dict, name: str, level: str) -> dict:
    """Copy of ``cfg`` with sensitivity item ``name`` at ``level`` ('low' or 'high')."""
    spec = param_raw(cfg, f"sensitivity.{name}")
    new = copy.deepcopy(cfg)
    v = spec[level]
    for i, key in enumerate(spec["targets"]):
        node = _node(new, key)
        if spec["mode"] == "scale":
            node["value"] = node["value"] * v
        elif spec["mode"] == "set":
            node["value"] = v[i] if isinstance(v, list) else v
        else:
            raise ValueError(f"unknown mode {spec['mode']!r} in sensitivity.{name}")
    return new


def items(cfg: dict) -> list[str]:
    """Sensitivity items of a config; a case config switches one off by setting it to null."""
    return [k for k, v in cfg.get("sensitivity", {}).items() if not k.startswith("_") and v is not None]


def layout_label(sol) -> str:
    return " + ".join(f"{s}({sol.sizes[s]}-slot: {list(sol.assignment.values()).count(s)})"
                      for s in sol.open_sites)


def evaluate(field: Field, cfg: dict, risk_weight: float = 0.0) -> dict[str, Any]:
    """Solve case 1 and case 2 for one config and compare."""
    c1 = optimize_capex(field, cfg)
    c2 = optimize_npv(field, cfg, risk_weight=risk_weight)
    n1 = npv_breakdown(field, cfg, c1.assignment, c1.sizes)
    n2 = npv_breakdown(field, cfg, c2.assignment, c2.sizes)
    return {
        "case 1 layout": layout_label(c1), "case 2 layout": layout_label(c2),
        "case 2 manifolds": len(c2.open_sites),
        "layout changed": (c1.assignment, c1.sizes) != (c2.assignment, c2.sizes),
        "NPV case 2 [MUSD]": n2["npv"] / M, "NPV case-1 layout [MUSD]": n1["npv"] / M,
        "value of reliability-aware design [MUSD]": (n2["npv"] - n1["npv"]) / M,
        "failure PV case 2 [MUSD]": (n2["repair_cost"] + n2["lost_production"]) / M,
    }


def one_at_a_time(field: Field, cfg: dict, risk_weight: float = 0.0) -> pd.DataFrame:
    base = evaluate(field, cfg, risk_weight)
    rows = [{"parameter": "base", "level": "base", "setting": "", **base}]
    for name in items(cfg):
        spec = param_raw(cfg, f"sensitivity.{name}")
        for level in ("low", "high"):
            res = evaluate(field, apply(cfg, name, level), risk_weight)
            rows.append({"parameter": name, "level": level,
                         "setting": f"{spec['mode']} {spec[level]}", **res})
    df = pd.DataFrame(rows)
    df["dNPV case 2 [MUSD]"] = df["NPV case 2 [MUSD]"] - base["NPV case 2 [MUSD]"]
    return df


def grid(field: Field, cfg: dict, x: tuple[str, Callable[[dict, float], None], list[float]],
         y: tuple[str, Callable[[dict, float], None], list[float]],
         risk_weight: float = 0.0) -> pd.DataFrame:
    """Two-parameter map. ``x``/``y`` = (label, setter(cfg, value), values)."""
    rows = []
    for xv in x[2]:
        for yv in y[2]:
            c = copy.deepcopy(cfg)
            x[1](c, xv)
            y[1](c, yv)
            rows.append({x[0]: xv, y[0]: yv, **evaluate(field, c, risk_weight)})
    return pd.DataFrame(rows)


def scale(*keys: str) -> Callable[[dict, float], None]:
    """Setter that multiplies the raw value of every key by a factor."""
    def setter(c: dict, factor: float) -> None:
        for k in keys:
            _node(c, k)["value"] = _node(c, k)["value"] * factor
    return setter
