from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def summarize_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    numeric = df.select_dtypes(include=[np.number]).copy()
    summary = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "numeric_columns": list(numeric.columns),
        "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
        "duplicate_rows": int(df.duplicated().sum()),
        "descriptive": numeric.describe(include="all").to_dict() if not numeric.empty else {},
    }
    if not numeric.empty:
        corr = numeric.corr(numeric_only=True)
        summary["correlation_matrix"] = corr.round(3).to_dict()
    return summary


def detect_missing_values(df: pd.DataFrame) -> dict[str, int]:
    return {col: int(df[col].isna().sum()) for col in df.columns}


def detect_duplicate_rows(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())


def _to_datetime_series(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.Series(pd.NaT, index=series.index)


def temporal_trend(df: pd.DataFrame, value_col: str, time_col: str) -> pd.DataFrame:
    if value_col not in df.columns or time_col not in df.columns:
        raise ValueError(f"Columns {value_col!r} and {time_col!r} must exist in the dataframe.")
    frame = df[[time_col, value_col]].copy()
    frame[time_col] = _to_datetime_series(frame[time_col])
    frame = frame.dropna(subset=[time_col, value_col])
    if frame.empty:
        return frame
    frame = frame.sort_values(time_col)
    frame = frame.assign(rolling_mean=frame[value_col].rolling(window=max(2, len(frame) // 5), min_periods=1).mean())
    return frame
