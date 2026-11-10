"""A run-out after the start hours lets windows that begin late in the record complete."""
import numpy as np

from layout_rel.weather import phased_waiting_hours

TABLE = {"tpop_rows": [12, 24], "hs_cols": [1, 2, 4], "alpha": [[0.7, 0.8, 0.85], [0.65, 0.75, 0.8]]}


def test_runout_completes_late_windows():
    rough, calm = np.full(72, 5.0), np.full(96, 0.5)
    alone = phased_waiting_hours(rough, 2.0, 12, TABLE, 12)
    assert np.isnan(alone).all()                              # no window before the record ends
    w = phased_waiting_hours(np.concatenate([rough, calm]), 2.0, 12, TABLE, 12)[:72]
    assert not np.isnan(w).any()
    assert w[0] == 72 and w[-1] == 1                          # wait until the calm run-out starts
