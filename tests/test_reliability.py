import math

from layout_rel.reliability import failure_modes, rate
from layout_rel.units import YEAR


def test_manifold_failure_stops_all_its_wells(field, cfg):
    assignment = {w: "M2" for w in field.wells}
    modes = {m.name: m for m in failure_modes(field, cfg, assignment)}
    assert set(modes["manifold M2"].wells) == set(field.wells)
    assert modes["tree W1"].wells == ("W1",)


def test_split_layout_has_two_manifolds(field, cfg):
    assignment = {"W1": "M1", "W2": "M1", "W3": "M1", "W4": "M3", "W5": "M3", "W6": "M3"}
    modes = [m for m in failure_modes(field, cfg, assignment) if m.name.startswith("manifold")]
    assert len(modes) == 2 and all(len(m.wells) == 3 for m in modes)


def test_line_rate_scales_with_length(cfg):
    r1, r2 = rate(cfg, "tieback_flowline", 1000.0), rate(cfg, "tieback_flowline", 15000.0)
    assert math.isclose(r2 / r1, 15.0)
    assert math.isclose(r1 * YEAR, 2.4e-4)          # 1 km -> 2.4e-4 per year


def test_manifold_rate_grows_with_slots(cfg):
    from layout_rel.config import param
    ref = param(cfg, "reliability.manifold.failure_rate_per_h")
    assert math.isclose(rate(cfg, "manifold", slots=4), ref)
    assert rate(cfg, "manifold", slots=2) < ref < rate(cfg, "manifold", slots=6)


def test_umbilical_rate_is_per_unit_not_per_km(cfg):
    """OREDA gives the umbilical rate per installed unit: a longer tie-back keeps the same rate."""
    r1, r2 = rate(cfg, "tieback_umbilical", 1000.0), rate(cfg, "tieback_umbilical", 15000.0)
    assert r1 == r2 > 0
    assert math.isclose(r1 * YEAR, 0.0374, rel_tol=1e-2)   # 4.27 per 1e6 h


def test_per_km_umbilical_rate_scales_and_needs_length(cfg):
    import copy

    import pytest

    c = copy.deepcopy(cfg)
    node = c["reliability"]["tieback_umbilical"]
    del node["failure_rate_per_unit"]
    node["failure_rate_per_km"] = {"value": 2.0e-3, "unit": "1/(km*yr)", "source": "test"}
    assert math.isclose(rate(c, "tieback_umbilical", 15000.0) / rate(c, "tieback_umbilical", 1000.0), 15.0)
    with pytest.raises(ValueError):
        rate(c, "tieback_umbilical")


def test_critical_fraction_scales_the_manifold_rate(cfg):
    import copy
    c = copy.deepcopy(cfg)
    assert rate(cfg, "manifold", slots=6) > 0
    c["reliability"]["manifold"]["critical_fraction"]["value"] = 0.5
    for k in (2, 4, 6, 8):
        assert math.isclose(rate(c, "manifold", slots=k), 0.5 * rate(cfg, "manifold", slots=k))
    assert rate(c, "xmas_tree") == rate(cfg, "xmas_tree")           # only manifolds are affected
