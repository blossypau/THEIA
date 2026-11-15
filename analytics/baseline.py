from __future__ import annotations

from typing import Any

import pandas as pd


def personal_baseline_summary(history_df: pd.DataFrame, metric_name: str, value_col: str = "value", time_col: str = "timestamp") -> dict[str, Any]:
    if history_df.empty:
        return {
            "status": "insufficient_data",
            "message": "Not enough history to construct a personal baseline.",
            "mean": None,
            "std": None,
            "count": 0,
        }
    frame = history_df[[time_col, value_col]].copy()
    frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce")
    frame = frame.dropna(subset=[time_col, value_col]).sort_values(time_col)
    if frame.empty:
        return {
            "status": "insufficient_data",
            "message": "No valid timestamps or values found.",
            "mean": None,
            "std": None,
            "count": 0,
        }
    values = frame[value_col].astype(float)
    return {
        "status": "ready",
        "metric": metric_name,
        "count": int(len(frame)),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        "min": float(values.min()),
        "max": float(values.max()),
        "latest": float(values.iloc[-1]),
        "trend": "stable" if len(values) > 2 and abs(values.iloc[-1] - values.mean()) <= (values.std(ddof=1) if len(values) > 1 else 0.0) else "monitor",
    }


def compare_to_baseline(current_value: float, baseline_summary: dict[str, Any]) -> dict[str, Any]:
    if baseline_summary.get("status") != "ready":
        return {
            "delta": None,
            "direction": "insufficient_baseline",
            "warning": "Insufficient personal baseline for reliable comparison.",
        }
    mean = baseline_summary["mean"]
    delta = current_value - mean
    std = baseline_summary["std"] or 1.0
    z_score = delta / std
    if abs(z_score) >= 2.0:
        alert = "review_recommended"
        warning = "Current measurement differs meaningfully from the individual history and may merit clinical review in context."
    elif abs(z_score) >= 1.0:
        alert = "monitor"
        warning = "Measurement is outside the typical local range but not necessarily clinically alarming."
    else:
        alert = "stable"
        warning = "Current measurement remains within the astronaut’s established pattern."
    return {
        "delta": float(delta),
        "direction": "above_baseline" if delta > 0 else "below_baseline",
        "z_score": float(z_score),
        "alert": alert,
        "warning": warning,
    }
