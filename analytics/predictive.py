from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split


def assess_prediction_readiness(df: pd.DataFrame, target_column: str, feature_columns: list[str], min_rows: int = 20) -> dict[str, Any]:
    if df.empty:
        return {
            "status": "insufficient_data",
            "reason": "No dataset was provided for model assessment.",
            "recommendation": "Collect more structured observations before attempting a predictive model.",
        }
    if target_column not in df.columns:
        return {
            "status": "insufficient_data",
            "reason": f"Target column {target_column!r} is missing.",
            "recommendation": "Define the target variable explicitly before model training.",
        }
    missing_features = [col for col in feature_columns if col not in df.columns]
    if missing_features:
        return {
            "status": "insufficient_data",
            "reason": f"Missing required feature columns: {missing_features}",
            "recommendation": "Verify units, feature provenance, and comparability before training.",
        }
    if len(df) < min_rows:
        return {
            "status": "insufficient_data",
            "reason": f"Only {len(df)} rows were available, below the minimum threshold of {min_rows}.",
            "recommendation": "Use an educational demonstration or gather more data from the same mission context.",
        }
    return {
        "status": "ready_for_experiment",
        "rows": int(len(df)),
        "target": target_column,
        "features": feature_columns,
        "method": "RandomForestRegressor with train/test split and evaluation on held-out data.",
        "warning": "Experimental only; not a clinical forecast.",
    }


def build_demo_regression(df: pd.DataFrame, target_column: str, feature_columns: list[str]) -> dict[str, Any]:
    readiness = assess_prediction_readiness(df, target_column, feature_columns)
    if readiness["status"] != "ready_for_experiment":
        return {"status": "educational_only", "details": readiness}

    working = df[feature_columns + [target_column]].dropna().copy()
    X = working[feature_columns]
    y = working[target_column]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    report = {
        "status": "experimental",
        "model": "RandomForestRegressor",
        "mae": float(mean_absolute_error(y_test, preds)),
        "r2": float(r2_score(y_test, preds)),
        "rows_used": int(len(working)),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "limitations": "This is an educational demonstration and does not replace domain-qualified medical forecasting.",
    }
    return report
