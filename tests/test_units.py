import math

from layout_rel.config import iter_params, param
from layout_rel.units import DAY, HOUR, YEAR, si_factor, unit_token, TO_SI


def test_every_numeric_param_has_known_unit(cfg):
    for key, p in iter_params(cfg):
        v = p["value"]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            assert unit_token(p["unit"]) in TO_SI, key


def test_conversions(cfg):
    assert math.isclose(param(cfg, "capex.manifold.install_days"), 2 * DAY)
    assert math.isclose(param(cfg, "vessels.hlv_day_rate") * DAY, 400e3 * 313.689 / 214.537)   # 2009 -> 2024 money
    assert math.isclose(param(cfg, "reliability.manifold.failure_rate_per_h") * HOUR, 23.82e-6)
    # 2.4e-4 per km-year -> per m per s
    assert math.isclose(param(cfg, "reliability.infield_flowline.failure_rate_per_km") * 1000 * YEAR, 2.4e-4)
    # 6000 bbl/d * 70 USD/bbl = 420,000 USD/day regardless of unit system
    q, p = param(cfg, "production.well_rate"), param(cfg, "production.oil_price")
    assert math.isclose(q * p * DAY, 6000 * 70)
    assert si_factor("days per tree") == DAY
