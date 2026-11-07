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
