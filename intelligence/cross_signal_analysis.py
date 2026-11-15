from __future__ import annotations

import pandas as pd


def cross_signal_summary(df: pd.DataFrame, primary_metric: str, secondary_metric: str) -> dict:
    if df.empty or primary_metric not in df.columns or secondary_metric not in df.columns:
        return {"status": "insufficient_data", "indicators": [primary_metric, secondary_metric], "summary": "Not enough aligned data for a reliable association review."}
    merged = df[["timestamp", primary_metric, secondary_metric]].dropna()
    if merged.empty:
        return {"status": "insufficient_data", "indicators": [primary_metric, secondary_metric], "summary": "Data overlap is insufficient for a meaningful cross-signal interpretation."}
    corr = merged[primary_metric].corr(merged[secondary_metric])
    return {
        "status": "reviewable",
        "indicators": [primary_metric, secondary_metric],
        "summary": f"{primary_metric} and {secondary_metric} show a correlation of {corr:.2f}; this result is interpretable but not causal evidence.",
        "correlation": float(corr),
    }
