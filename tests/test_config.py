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
