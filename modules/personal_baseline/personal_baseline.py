from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.models import HealthMeasurement


def render_personal_baseline():
    st.subheader("Personal Baseline Engine")
    session = SessionLocal()
    try:
        metric = st.selectbox("Metric", ["heart_rate", "blood_pressure", "blood_glucose", "sleep_hours", "mood", "body_temperature"])
        rows = session.query(HealthMeasurement).filter_by(metric_name=metric).order_by(HealthMeasurement.timestamp.asc()).all()
        if not rows:
            st.info("No historical data available for this metric.")
            return
        values = np.array([row.value for row in rows], dtype=float)
        if len(values) < 5:
            st.warning("Insufficient data to establish a reliable personal baseline. Collect more measurements before drawing conclusions.")
            st.metric("Samples", len(values))
            return

        avg = float(np.mean(values))
        std = float(np.std(values))
        trend = float(values[-1] - values[0])
        latest = values[-1]
        st.metric("Historical average", f"{avg:.2f}")
        st.metric("Variability", f"{std:.2f}")
        st.metric("Recent change", f"{trend:.2f}")
        st.metric("Samples", len(values))

        df = pd.DataFrame({"timestamp": [row.timestamp for row in rows], "value": values})
        st.line_chart(df.set_index("timestamp")["value"])

        if abs(latest - avg) > 2 * std:
            st.warning("Current measurement differs substantially from personal history. This may warrant review in context with workload, sleep, and mission activity.")
        else:
            st.success("Current measurement remains within the established personal variation range.")
    finally:
        session.close()
