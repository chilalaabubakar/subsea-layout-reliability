import numpy as np
import pandas as pd

from layout_rel.weather import monthly_waiting, waiting_hours


def test_waiting_by_hand():
    hs = np.array([3, 1, 1, 3, 1, 1, 1, 3], dtype=float)      # limit 2, need 3 calm hours
    w = waiting_hours(hs, limit=2.0, duration=3)
    # first 3-hour window starts at index 4
    assert list(w[:5]) == [4, 3, 2, 1, 0]
    assert np.isnan(w[5]) and np.isnan(w[7])                  # no full window left


def test_always_calm_means_no_wait():
    hs = np.zeros(100)
    assert np.all(waiting_hours(hs, 2.0, 24)[:77] == 0)


def test_monthly_table_shape():
    idx = pd.date_range("2020-01-01", "2020-12-31 23:00", freq="h")
    hs = pd.Series(np.where(idx.month.isin([12, 1, 2]), 4.0, 1.0), index=idx)   # rough winter
    m = monthly_waiting(hs, limit=2.5, duration=24)
    assert len(m) == 12
    assert m.loc[7, "mean_wait_h"] == 0 and m.loc[7, "workable_share"] == 1
    assert m.loc[1, "workable_share"] == 0 and m.loc[1, "mean_wait_h"] > 24 * 15


TABLE = {"tpop_rows": [12, 24, 36, 48, 72], "hs_cols": [1, 2, 4, 6],
         "alpha": [[0.68, 0.80, 0.83, 0.84], [0.66, 0.77, 0.80, 0.82], [0.65, 0.75, 0.77, 0.80],
                   [0.63, 0.71, 0.75, 0.78], [0.58, 0.66, 0.71, 0.76]]}


def test_alpha_factor_lookup():
    from layout_rel.weather import alpha_factor
    assert alpha_factor(TABLE, 24, 2.0) == 0.77
    assert abs(alpha_factor(TABLE, 10, 3.0) - (0.80 + 0.83) / 2) < 1e-12     # interpolate in Hs
    assert alpha_factor(TABLE, 30, 2.5) > alpha_factor(TABLE, 30, 2.0)


def test_phase_plan():
    from layout_rel.weather import phase_plan
    assert phase_plan(48, 47) == [24, 24]
    assert phase_plan(144, 47) == [36, 36, 36, 36]


def test_phased_wait_calm_sea_is_zero():
    from layout_rel.weather import phased_waiting_hours
    w = phased_waiting_hours(np.zeros(2000), 2.0, 96, TABLE, 47)
    assert np.all(w[:1500] == 0)


def test_phased_wait_by_hand():
    from layout_rel.weather import phased_waiting_hours
    # one 24 h phase (repair 24 h): needs 48 h with Hs <= 0.77 * 2 = 1.54 m
    hs = np.r_[np.full(10, 3.0), np.full(100, 1.0)]
    w = phased_waiting_hours(hs, 2.0, 24, TABLE, 47)
    assert w[0] == 10 and w[10] == 0
