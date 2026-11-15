from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import SessionLocal
from database.repository import get_dashboard_summary


def render_dashboard():
    st.subheader("Mission Health Dashboard")
    session = SessionLocal()
    try:
        summary = get_dashboard_summary(session)
        astronaut = summary["astronaut"]
        latest_measurements = summary["latest_measurements"]
        latest_checkin = summary["latest_checkin"]
        anomalies = summary["anomalies"]

        cols = st.columns(4)
        metric_map = {
            "heart_rate": ("Heart Rate", "bpm"),
            "blood_pressure": ("Blood Pressure", "mmHg"),
            "blood_glucose": ("Blood Glucose", "mg/dL"),
            "sleep_hours": ("Sleep", "hours"),
        }
        for idx, measurement in enumerate(latest_measurements[:4]):
            with cols[idx]:
                label, unit = metric_map.get(measurement.metric_name, (measurement.metric_name, measurement.unit))
                st.metric(label, f"{measurement.value} {unit}", help=f"Source: {measurement.source}; timestamp: {measurement.timestamp}")

        st.markdown("---")
        charts = ["heart_rate", "blood_glucose", "sleep_hours", "mood"]
        for metric in charts:
            rows = session.execute(
                f"SELECT metric_name, value, timestamp, source, data_quality_status FROM health_measurements WHERE metric_name='{metric}' ORDER BY timestamp ASC"
            ).all()
            if rows:
                df = pd.DataFrame(rows, columns=["metric_name", "value", "timestamp", "source", "data_quality_status"])
                fig = px.line(df, x="timestamp", y="value", color_discrete_sequence=["#b08cff"], markers=True)
                fig.update_layout(title=f"{metric.replace('_', ' ').title()} history", margin=dict(l=0, r=0, t=30, b=0), template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("Latest alerts")
        if anomalies:
            for alert in anomalies:
                st.warning(f"{alert.metric_name.upper()} • {alert.flag_level} • {alert.explanation}")
        else:
            st.success("No active anomaly flags in the current review window.")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Daily check-in status")
            if latest_checkin:
                st.write(f"Sleep: {latest_checkin.sleep_duration_hours}h")
                st.write(f"Mood: {latest_checkin.mood}/100")
                st.write(f"Energy: {latest_checkin.energy}/100")
                st.write(f"Fatigue: {latest_checkin.fatigue}/100")
            else:
                st.info("No daily check-in recorded yet.")
        with col2:
            st.subheader("Mission context")
            if summary["latest_context"]:
                ctx = summary["latest_context"]
                st.write(f"Mission phase: {ctx.phase}")
                st.write(f"Recent activity: {ctx.recent_physical_activity}")
                st.write(f"Nutrition: {ctx.nutrition}")
            else:
                st.info("No mission context has been logged.")
    finally:
        session.close()
