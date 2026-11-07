"""Load YAML parameter files.

Every parameter in the YAML is a small dict ``{value, unit, source}``.
``param(cfg, "capex.manifold")`` returns just the value, so model code never
contains hard-coded numbers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import re

import yaml

from .units import si_factor


class _Loader(yaml.SafeLoader):
    """SafeLoader that also reads ``8.0e6`` / ``1e-6`` as floats.

    Plain PyYAML follows YAML 1.1 and treats ``8.0e6`` as a *string*.
    """


_Loader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"""^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+]?[0-9]+)?
                    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
                    |\.[0-9_]+(?:[eE][-+]?[0-9]+)?
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$""", re.X),
    list("-+0123456789."),
)


def read_yaml(path: str | Path) -> Any:
    with Path(path).open() as f:
        return yaml.load(f, Loader=_Loader)


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
DEFAULT_CONFIG = CONFIG_DIR / "base_case.yaml"


def _merge(base: dict, over: dict) -> dict:
    """Deep merge: values in ``over`` replace those in ``base``; a parameter node
    (dict with 'value') is replaced as a whole."""
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and not _is_param(v):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Read a parameter YAML file and remember where it came from.

    A file may start with ``_extends: other.yaml`` (path relative to the file): it then
    holds only the parameters that differ from that base file.
    """
    path = Path(path)
    cfg = read_yaml(path)
    if "_extends" in cfg:
        base = load_config(path.parent / cfg.pop("_extends"))
        base.pop("_config_dir", None)
        cfg = _merge(base, cfg)
    cfg["_config_dir"] = str(path.parent)
    return cfg


def _is_param(node: Any) -> bool:
    return isinstance(node, dict) and "value" in node


def param_raw(cfg: dict[str, Any], key: str) -> Any:
    """Value of a dotted key exactly as written in the YAML (no unit conversion)."""
    node: Any = cfg
    for part in key.split("."):
        node = node[part]
    if not _is_param(node):
        raise KeyError(f"'{key}' is not a parameter (needs a 'value' field)")
    return node["value"]


def param(cfg: dict[str, Any], key: str) -> Any:
    """Value of a dotted key converted to SI, e.g. ``param(cfg, "capex.manifold.sit")``.

    Numbers are multiplied by the factor for their ``unit`` (see units.TO_SI), so
    "2 days" comes back as 172800 s. Strings, lists and dicts are returned as written.
    """
    node: Any = cfg
    for part in key.split("."):
        node = node[part]
    value = param_raw(cfg, key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    factor = si_factor(node.get("unit", "-"))
    return value if factor == 1.0 else value * factor     # keeps ints (seeds, counts) as ints


def iter_params(cfg: dict[str, Any], prefix: str = ""):
    """Yield ``(dotted_key, {value, unit, source})`` for every parameter."""
    for k, v in cfg.items():
        if k.startswith("_"):
            continue
        key = f"{prefix}{k}"
        if _is_param(v):
            yield key, v
        elif isinstance(v, dict):
            yield from iter_params(v, key + ".")


def placeholders(cfg: dict[str, Any]) -> list[str]:
    """Parameters whose source is still a placeholder (no citation yet)."""
    return [k for k, p in iter_params(cfg)
            if "PLACEHOLDER" in str(p.get("source", "")).upper()]


def field_path(cfg: dict[str, Any]) -> Path:
    """Path of the field geometry file referenced by the config."""
    return Path(cfg["_config_dir"]) / param(cfg, "field_file")


if __name__ == "__main__":
    c = load_config()
    todo = placeholders(c)
    print(f"{len(todo)} parameter(s) still need a literature source:")
    for k in todo:
        print("  -", k)
