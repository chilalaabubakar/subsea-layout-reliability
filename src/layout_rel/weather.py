"""Waiting-on-weather from an hourly significant wave height (Hs) series.

A repair needs a weather window: ``duration`` consecutive hours with Hs below the
vessel's operating limit. If the vessel is ready at hour t, the wait is the time
until the first hour tau >= t at which such a window starts.

Failures happen at random times, so the expected wait is the mean of that wait over
all start hours (of the whole record, or of one calendar month for seasonal values).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def waiting_hours(hs: np.ndarray, limit: float, duration: int) -> np.ndarray:
    """Hours to wait from each hour until a window of ``duration`` hours with Hs < limit starts.

    Hours with no complete window before the end of the record get NaN.
    """
    ok = np.asarray(hs) < limit
    n = len(ok)
    run = np.zeros(n + 1, dtype=np.int64)            # consecutive ok hours starting at i
    for i in range(n - 1, -1, -1):
        run[i] = run[i + 1] + 1 if ok[i] else 0
    start_ok = run[:n] >= duration
    nxt = np.full(n + 1, -1, dtype=np.int64)         # next index >= i where a window starts
    for i in range(n - 1, -1, -1):
        nxt[i] = i if start_ok[i] else nxt[i + 1]
    wait = (nxt[:n] - np.arange(n)).astype(float)
    wait[nxt[:n] < 0] = np.nan
    return wait


def monthly_waiting(series: pd.Series, limit: float, duration: int) -> pd.DataFrame:
    """Mean and P90 wait [h] by calendar month, plus the share of hours with Hs < limit.

    ``series``: hourly Hs [m] with a DatetimeIndex.
    """
    w = waiting_hours(series.to_numpy(), limit, duration)
    df = pd.DataFrame({"wait_h": w, "ok": series.to_numpy() < limit}, index=series.index)
    g = df.groupby(df.index.month)
    out = pd.DataFrame({"mean_wait_h": g.wait_h.mean(), "p90_wait_h": g.wait_h.quantile(0.9),
                        "workable_share": g.ok.mean()})
    out.index.name = "month"
    return out


def seasonal_mean_wait(series: pd.Series, limit: float, duration: int,
                       months: tuple[int, ...]) -> float:
    """Mean wait [h] for start hours in the given calendar months."""
    w = waiting_hours(series.to_numpy(), limit, duration)
    m = np.isin(series.index.month, months)
    return float(np.nanmean(w[m]))
