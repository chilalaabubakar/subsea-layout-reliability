import math

import pytest

from layout_rel.config import param
from layout_rel.economics import (capex_breakdown, capex_coefficients, manifold_cost,
                                  smallest_size, tree_cost)


def test_tree_cost_from_components(cfg):
    expected = (param(cfg, "capex.xmas_tree.procurement") + param(cfg, "capex.xmas_tree.sit")
                + param(cfg, "capex.xmas_tree.install_days")
                * param(cfg, "vessels.modu_deep_day_rate"))
    assert math.isclose(tree_cost(cfg), expected)


def test_bigger_manifold_costs_more(cfg):
    costs = [manifold_cost(cfg, k) for k in param(cfg, "manifold.sizes")]
    assert costs == sorted(costs)


def test_smallest_size(cfg):
    assert smallest_size(cfg, 3) == 4
    assert smallest_size(cfg, 6) == 6
    with pytest.raises(ValueError):
        smallest_size(cfg, 99)


def test_breakdown_matches_coefficients(field, cfg):
    assignment = {w: "M2" for w in field.wells}           # 6 wells -> 6-slot manifold
    b = capex_breakdown(field, cfg, assignment)
    c = capex_coefficients(field, cfg)
    via_coeffs = (c.tree_total + c.manifold[6] + c.tieback["M2"]
                  + sum(c.connect[w, "M2"] for w in field.wells))
    assert math.isclose(b["total"], via_coeffs)
    assert math.isclose(b["trees"], 6 * tree_cost(cfg))


def test_breakdown_rejects_overfull_manifold(field, cfg):
    with pytest.raises(ValueError):
        capex_breakdown(field, cfg, {w: "M2" for w in field.wells}, sizes={"M2": 4})


def test_annuity_factors_by_hand(cfg):
    from layout_rel.economics import annuity_factors, production_profile
    g = production_profile(cfg)
    assert len(g) == 20 and g[:3] == [1.0, 1.0, 1.0] and math.isclose(g[3], 0.88)
    a_rep, a_prod = annuity_factors(cfg)
    assert math.isclose(a_rep, (1 - 1.1 ** -20) / 0.1)           # 20-year annuity at 10 %
    assert a_prod < a_rep


# ---------------------------------------------------------------- deferred production
def test_deferred_production_credit(field, cfg):
    import copy
    import math

    from layout_rel.config import param
    from layout_rel.economics import (annuity_factors, discount_factors, lost_production_weights,
                                      production_profile, revenue_pv)
    df, g = discount_factors(cfg), production_profile(cfg)
    a_rep, a_prod = annuity_factors(cfg)
    assert lost_production_weights(cfg) == df                       # base case: nothing is deferred
    c = copy.deepcopy(cfg)
    c["production"]["deferred_fraction"]["value"] = 1.0             # all of it, in the last year
    assert annuity_factors(c)[0] == a_rep
    assert math.isclose(annuity_factors(c)[1], sum(x * (f - df[-1]) for f, x in zip(df, g)))
    assert revenue_pv(field, c) == revenue_pv(field, cfg)           # revenue is not touched
    c["production"]["deferral_delay"]["value"] = 1.0                # all of it, one year later
    r = param(cfg, "economics.discount_rate")
    assert math.isclose(annuity_factors(c)[1], a_prod * (1 - 1 / (1 + r)))
    c["production"]["deferred_fraction"]["value"] = 0.5
    assert math.isclose(annuity_factors(c)[1], a_prod * (1 - 0.5 / (1 + r)))
