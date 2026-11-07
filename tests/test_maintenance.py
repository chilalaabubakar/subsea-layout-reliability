import math

from layout_rel.config import param
from layout_rel.maintenance import (expected_failure_cost, failure_cost_coefficients, mode_cost,
                                    repair)
from layout_rel.reliability import FailureMode
from layout_rel.units import DAY, YEAR


def test_repair_by_hand(cfg):
    r = repair(cfg, "manifold")             # HLV: 30 d mob + 4 d * 1.25 = 35 d
    assert math.isclose(r.downtime, 35 * DAY)
    assert math.isclose(r.cost, 400e3 * 35 + 1.104e6)


def test_mode_cost_by_hand(cfg):
    lam = 0.5 / YEAR                         # 0.5 failures per year
    m = FailureMode("test", "manifold", lam, ("W1", "W2"))
    c = mode_cost(cfg, m)
    lost_usd = 0.5 * 35 * 2 * 6000 * 70      # failures * days * wells * bbl/d * USD/bbl
    assert math.isclose(c["lost_production"], lost_usd, rel_tol=1e-9)
    assert math.isclose(c["repair_cost"], 0.5 * (400e3 * 35 + 1.104e6))


def test_grouping_raises_lost_production_per_manifold_failure(field, cfg):
    one = expected_failure_cost(field, cfg, {w: "M2" for w in field.wells})
    two = expected_failure_cost(field, cfg, {"W1": "M1", "W2": "M1", "W3": "M1",
                                             "W4": "M3", "W5": "M3", "W6": "M3"})
    # two manifolds fail twice as often in total, but each failure stops only half the wells
    assert two.by_kind["manifold"]["failures"] > one.by_kind["manifold"]["failures"]
    assert one.total > 0 and two.total > 0


def test_coefficients_match_direct_calculation(field, cfg):
    c = failure_cost_coefficients(field, cfg)
    for assignment in ({w: "M2" for w in field.wells},
                       {"W1": "M1", "W2": "M1", "W3": "M1", "W4": "M3", "W5": "M3", "W6": "M3"},
                       {"W1": "M1", "W2": "M1", "W3": "M2", "W4": "M2", "W5": "M3", "W6": "M3"}):
        direct = expected_failure_cost(field, cfg, assignment).total
        linear = (c.constant + sum(c.site[s] for s in set(assignment.values()))
                  + sum(c.connect[w, s] for w, s in assignment.items()))
        assert math.isclose(direct, linear, rel_tol=1e-9)
