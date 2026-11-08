import math

from layout_rel.config import param, param_raw
from layout_rel.sensitivity import apply, evaluate, items, scale


def test_every_item_targets_existing_parameters(cfg):
    for name in items(cfg):
        spec = param_raw(cfg, f"sensitivity.{name}")
        for key in spec["targets"]:
            param_raw(cfg, key)                       # raises KeyError if missing
        assert spec["mode"] in ("scale", "set")


def test_apply_scale_and_set(cfg):
    lo = apply(cfg, "mobilisation_time", "low")
    assert math.isclose(param_raw(lo, "vessels.hlv_mobilisation"),
                        0.5 * param_raw(cfg, "vessels.hlv_mobilisation"))
    hi = apply(cfg, "vessel_day_rates", "high")
    assert param_raw(hi, "vessels.msv_day_rate") == 120e3
    assert param_raw(hi, "vessels.hlv_day_rate") == 550e3
    assert param_raw(cfg, "vessels.msv_day_rate") == 80e3      # original untouched


def test_scale_setter(cfg):
    import copy
    c = copy.deepcopy(cfg)
    scale("production.oil_price")(c, 2.0)
    assert math.isclose(param(c, "production.oil_price"), 2 * param(cfg, "production.oil_price"))


def test_reliability_aware_design_never_loses(field, cfg):
    r = evaluate(field, apply(cfg, "slot_fraction", "high"))
    assert r["value of reliability-aware design [MUSD]"] >= -1e-6


def test_weather_case_drops_allowance_item():
    """With explicit weather waits the 20-30 % allowance is not a sensitivity input (would double count)."""
    from layout_rel.config import CONFIG_DIR, load_config, param
    from layout_rel.sensitivity import items
    cfg = load_config(CONFIG_DIR / "solveig_weather.yaml")
    assert param(cfg, "maintenance.weather_allowance") == 0
    assert "weather_allowance" not in items(cfg)
    assert "weather_allowance" in items(load_config(CONFIG_DIR / "base_case.yaml"))
