from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import IsolationForest

from database.database import SessionLocal
from database.models import HealthMeasurement


def detect_rule_based_anomalies(rows):
    if len(rows) < 3:
        return []
    values = np.array([row.value for row in rows], dtype=float)
    mean = float(values.mean())
    std = float(values.std(ddof=0)) or 1.0
    anomalies = []
    for row in rows:
        z = abs((float(row.value) - mean) / std)
        if z > 2.5:
            anomalies.append((row, "Rule-based detector", z))
    return anomalies


def detect_ml_anomalies(rows):
    if len(rows) < 6:
        return []
    df = pd.DataFrame({"index": list(range(len(rows))), "value": [float(row.value) for row in rows]})
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(df[["value"]])
    prediction = model.predict(df[["value"]])
    flagged = []
    for row, pred in zip(rows, prediction):
        if pred == -1:
            flagged.append((row, "Experimental Isolation Forest", 0.0))
    return flagged


def render_anomaly_detection():
    st.subheader("Anomaly Detection")
    st.caption("Experimental analysis only; not a clinical diagnosis.")
    session = SessionLocal()
    try:
        metric = st.selectbox("Metric to inspect", ["heart_rate", "blood_pressure", "blood_glucose", "body_temperature", "sleep_hours", "mood"])
        rows = session.query(HealthMeasurement).filter_by(metric_name=metric).order_by(HealthMeasurement.timestamp.asc()).all()
        if not rows:
            st.info("No measurements available for anomaly review.")
            return

        rule_flags = detect_rule_based_anomalies(rows)
        ml_flags = detect_ml_anomalies(rows)

        st.write("### Rule-based detection")
        if rule_flags:
            for row, detector, z in rule_flags:
                st.warning(f"{row.metric_name}: {row.value} {row.unit} on {row.timestamp} — unusual relative to personal variation (z-score ~ {z:.2f}).")
        else:
            st.success("No major rule-based deviations were detected in the current sample.")

        st.write("### Experimental machine learning")
        if ml_flags:
            for row, detector, _ in ml_flags:
                st.warning(f"{row.metric_name}: {row.value} {row.unit} on {row.timestamp} — flagged by experimental unsupervised detection.")
        else:
            st.info("The experimental model did not flag this metric in the current time window.")

        st.write("### Interpretation")
        st.info("Anomalies are displayed as patterns of interest, not as medical diagnoses. Review them alongside sleep, workload, symptoms, and mission context.")
    finally:
        session.close()
