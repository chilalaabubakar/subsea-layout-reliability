import pytest

from layout_rel.config import iter_params, param


def test_every_param_has_value_unit_source(cfg):
    for key, p in iter_params(cfg):
        assert {"value", "unit", "source"} <= set(p), key


def test_scientific_notation_is_float(cfg):
    assert isinstance(param(cfg, "capex.manifold.procurement_base"), float)
    assert isinstance(param(cfg, "solver.mip_gap"), float)


def test_param_rejects_non_parameter(cfg):
    with pytest.raises(KeyError):
        param(cfg, "capex")


def test_extends_overrides_only_listed_params():
    from layout_rel.config import CONFIG_DIR, load_config
    base = load_config()
    case = load_config(CONFIG_DIR / "solveig_case.yaml")
    assert param(case, "field_file") == "field_solveig.yaml"
    assert param(case, "production.well_rate") != param(base, "production.well_rate")
    assert param(case, "capex.manifold.sit") == param(base, "capex.manifold.sit")   # inherited
    assert param(case, "production.oil_price") == param(base, "production.oil_price")


def test_costs_are_escalated_to_the_target_year(cfg):
    import copy
    import math

    from layout_rel.config import escalation_factor, param_raw
    from layout_rel.units import DAY
    index = param_raw(cfg, "escalation.index")
    assert param_raw(cfg, "escalation.target_year") == 2024
    assert math.isclose(escalation_factor(cfg, 2009), index[2024] / index[2009])
    assert escalation_factor(cfg, None) == 1.0 and escalation_factor(cfg, 2024) == 1.0
    assert math.isclose(param(cfg, "vessels.msv_day_rate") * DAY, 80e3 * index[2024] / index[2009])
    assert math.isclose(param(cfg, "capex.tieback_flowline"), 2243.0 * index[2024] / index[2014])
    assert math.isclose(param(cfg, "capex.manifold.foundation"), 1.0e6 * index[2024] / index[2007])
    # every USD cost except the oil price says which year's money it is in
    for key, p in iter_params(cfg):
        if str(p["unit"]).startswith("USD") and not key.startswith(("sensitivity.", "production.")):
            assert p.get("cost_year") in index, key
    plain = copy.deepcopy(cfg)
    plain["escalation"]["target_year"]["value"] = None          # source values as they are
    assert math.isclose(param(plain, "vessels.msv_day_rate") * DAY, 80e3)
    assert param(cfg, "production.oil_price") == param(plain, "production.oil_price")
