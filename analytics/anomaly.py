from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_anomalies(df: pd.DataFrame, value_col: str, time_col: str = "timestamp", contamination: float = 0.1) -> dict[str, Any]:
    if value_col not in df.columns:
        raise ValueError(f"Metric column {value_col!r} not found.")
    frame = df[[time_col, value_col]].copy()
    frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce")
    frame = frame.dropna(subset=[time_col, value_col]).sort_values(time_col)
    if frame.empty:
        return {"status": "insufficient_data", "method": "IsolationForest", "anomalies": []}

    model = IsolationForest(contamination=contamination, random_state=42)
    values = frame[value_col].astype(float).to_numpy().reshape(-1, 1)
    preds = model.fit_predict(values)
    anomalies = frame[preds == -1].copy()
    anomalies = anomalies.assign(anomaly_score=abs((anomalies[value_col] - frame[value_col].mean()) / (frame[value_col].std(ddof=1) or 1.0)))
    return {
        "status": "ok",
        "method": "IsolationForest",
        "anomalies": [
            {
                "timestamp": ts.to_pydatetime().isoformat(),
                "value": float(value),
                "score": float(score),
            }
            for ts, value, score in zip(anomalies[time_col], anomalies[value_col], anomalies["anomaly_score"])
        ],
        "total_anomalies": int(len(anomalies)),
        "dataset_rows": int(len(frame)),
        "limitations": "Statistical anomalies are not medical diagnoses and require contextual mission review.",
    }
