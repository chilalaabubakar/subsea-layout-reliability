"""Waiting-on-weather from an hourly significant wave height (Hs) series.

DNV-ST-N001 (2023) method, used by ``phased_waiting_hours``:
- a weather-restricted operation needs T_POP < 72 h and T_R < 96 h [2.6.7.2]; with
  T_R = (1 + contingency) x T_POP (default T_R = 2 T_POP, [2.6.4.2]) and T_C >= 6 h [2.6.4.3],
  longer repairs are split into consecutive phases with a safe stop between them
  ([2.6.5.2], [2.6.7.8]), each phase needing its own window;
- each phase needs a window of T_R hours with Hs <= OP_WF = alpha x OP_LIM [2.6.9.2],
  alpha from the configured table (Table 2-4 for forecast level B, [2.6.10]).

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


def alpha_factor(table: dict, t_pop_h: float, op_lim: float) -> float:
    """Alpha factor for a planned operation period and an Hs limit (DNV-ST-N001 Table 2-x form).

    ``table`` = {"tpop_rows": [12, 24, ...], "hs_cols": [1, 2, 4, 6], "alpha": [[...], ...]}.
    Row: first row with T_POP <= row limit. Column: linear interpolation in Hs (clamped).
    """
    rows, cols, a = table["tpop_rows"], table["hs_cols"], np.asarray(table["alpha"], float)
    i = next((k for k, r in enumerate(rows) if t_pop_h <= r), None)
    if i is None:
        raise ValueError(f"T_POP = {t_pop_h} h is longer than the table allows ({rows[-1]} h)")
    return float(np.interp(op_lim, cols, a[i]))


def phase_plan(repair_h: float, max_phase_h: float) -> list[float]:
    """Split an active repair into n equal phases of at most ``max_phase_h`` hours."""
    n = int(np.ceil(repair_h / max_phase_h))
    return [repair_h / n] * n


def phased_waiting_hours(hs: np.ndarray, op_lim: float, repair_h: float, table: dict,
                         max_phase_h: float, contingency: float = 1.0,
                         min_contingency_h: float = 6.0) -> np.ndarray:
    """Extra hours spent waiting on weather for a repair started (vessel ready) at each hour.

    Phases run in sequence; each starts at the first hour with a window of T_R hours with
    Hs <= alpha x OP_LIM and then takes T_POP hours. Wait = finish - start - sum(T_POP).
    """
    hs = np.asarray(hs)
    n = len(hs)
    cur = np.arange(n, dtype=np.int64)
    total = 0
    for t_pop in phase_plan(repair_h, max_phase_h):
        t_r = t_pop + max(contingency * t_pop, min_contingency_h)
        op_wf = alpha_factor(table, t_pop, op_lim) * op_lim
        L = int(np.ceil(t_r))
        ok = hs <= op_wf
        run = np.zeros(n + 1, dtype=np.int64)
        for i in range(n - 1, -1, -1):
            run[i] = run[i + 1] + 1 if ok[i] else 0
        nxt = np.full(n + 1, -1, dtype=np.int64)
        for i in range(n - 1, -1, -1):
            nxt[i] = i if run[i] >= L else nxt[i + 1]
        valid = cur < n
        start = np.where(valid, nxt[np.minimum(cur, n)], -1)
        dur = int(np.ceil(t_pop))
        cur = np.where(start >= 0, start + dur, n + 10 ** 9)
        total += dur
    wait = (cur - np.arange(n) - total).astype(float)
    wait[cur >= n + 10 ** 9 - 1] = np.nan
    return wait
