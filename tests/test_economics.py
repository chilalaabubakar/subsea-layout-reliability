import math

from layout_rel.config import param
from layout_rel.economics import capex_breakdown, capex_coefficients


def test_breakdown_matches_coefficients(field, cfg):
    assignment = {w: "M2" for w in field.wells}
    b = capex_breakdown(field, cfg, assignment)
    c = capex_coefficients(field, cfg)
    via_coeffs = (c.tree_total + c.site_fixed["M2"]
                  + sum(c.connect[w, "M2"] for w in field.wells))
    assert math.isclose(b["total"], via_coeffs)
    assert math.isclose(b["trees"], 6 * param(cfg, "capex.xmas_tree"))
    assert math.isclose(b["manifolds"], param(cfg, "capex.manifold"))
