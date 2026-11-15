from __future__ import annotations

import pandas as pd


def compute_baseline(series: pd.Series) -> dict:
    if series.empty:
        return {"samples": 0, "mean": None, "std": None, "confidence": "insufficient_data"}
    mean = float(series.mean())
    std = float(series.std(ddof=0))
    return {
        "samples": int(len(series)),
        "mean": mean,
        "std": std,
        "confidence": "high" if len(series) >= 10 else "moderate" if len(series) >= 5 else "insufficient_data",
    }
