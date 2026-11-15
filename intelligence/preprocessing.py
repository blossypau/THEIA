from __future__ import annotations

import pandas as pd


def clean_measurements(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans incoming measurement data while preserving original values and sources."""
    data = df.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data = data.dropna(subset=["timestamp", "metric_name", "value"]).copy()
    data = data.drop_duplicates(subset=["timestamp", "metric_name", "source"], keep="last")
    data["metric_name"] = data["metric_name"].astype(str).str.strip()
    return data
