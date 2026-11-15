from __future__ import annotations

import pandas as pd


def compute_trend(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    x = range(len(series))
    y = series.to_numpy(dtype=float)
    if len(y) < 2:
        return 0.0
    slope = (y[-1] - y[0]) / max(len(y) - 1, 1)
    return float(slope)
