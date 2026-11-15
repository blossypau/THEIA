from __future__ import annotations

import pandas as pd


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    if "timestamp" in data.columns:
        data["day_index"] = data["timestamp"].dt.floor("D").astype(str)
    return data
