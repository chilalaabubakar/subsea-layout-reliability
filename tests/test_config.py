import pytest

from layout_rel.config import iter_params, param


def test_every_param_has_value_unit_source(cfg):
    for key, p in iter_params(cfg):
        assert {"value", "unit", "source"} <= set(p), key


def test_scientific_notation_is_float(cfg):
    assert isinstance(param(cfg, "capex.manifold"), float)
    assert isinstance(param(cfg, "solver.mip_gap"), float)


def test_param_rejects_non_parameter(cfg):
    with pytest.raises(KeyError):
        param(cfg, "capex")
