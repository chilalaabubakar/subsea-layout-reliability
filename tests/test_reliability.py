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
