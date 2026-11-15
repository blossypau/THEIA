from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import SessionLocal
from database.models import HealthMeasurement
from database.repository import get_dashboard_summary, get_measurements_for_metric
from modules.ui.theme import apply_theia_theme, render_metric_card, render_page_header


def _metric_lookup(metric_name: str) -> tuple[str, str]:
    mapping = {
        "heart_rate": ("Heart rate", "bpm"),
        "blood_pressure": ("Blood pressure", "mmHg"),
        "blood_glucose": ("Blood glucose", "mg/dL"),
        "body_temperature": ("Temperature", "°C"),
        "sleep_hours": ("Sleep", "h"),
        "mood": ("Mood", "/100"),
        "oxygen_saturation": ("SpO₂", "%"),
    }
    return mapping.get(metric_name, (metric_name.replace("_", " ").title(), ""))


def _measure_delta(current: float, previous: float | None) -> str:
    if previous is None:
        return "No prior sample"
    delta = current - previous
    prefix = "+" if delta >= 0 else ""
    return f"Δ {prefix}{delta:.2f} vs prior"


def render_dashboard() -> None:
    apply_theia_theme()
    render_page_header("Mission overview", "Astronaut health intelligence • system summary • live mission context")

    session = SessionLocal()
    try:
        summary = get_dashboard_summary(session)
        latest_measurements = summary["latest_measurements"]
        latest_checkin = summary["latest_checkin"]
        anomalies = summary["anomalies"]

        display_metrics = [
            ("heart_rate", "Heart rate"),
            ("blood_pressure", "Blood pressure"),
            ("blood_glucose", "Blood glucose"),
            ("body_temperature", "Body temperature"),
            ("oxygen_saturation", "Oxygen saturation"),
            ("sleep_hours", "Sleep duration"),
        ]

        cols = st.columns(3)
        for idx, (metric_key, label) in enumerate(display_metrics):
            records = session.query(HealthMeasurement).filter_by(metric_name=metric_key).order_by(HealthMeasurement.timestamp.desc()).limit(2).all()
            value = records[0].value if records else 0
            prior = records[1].value if len(records) > 1 else None
            with cols[idx % 3]:
                render_metric_card(
                    label,
                    f"{value:.1f}" if metric_key in {"body_temperature", "sleep_hours"} else f"{value:.0f}",
                    _metric_lookup(metric_key)[1],
                    records[0].source if records else "No data",
                    records[0].timestamp.strftime("%Y-%m-%d %H:%M") if records else "No timestamp",
                    _measure_delta(value, prior),
                )

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-tag'>Health trends</div>", unsafe_allow_html=True)

        metric = st.selectbox("Indicator", ["heart_rate", "blood_pressure", "blood_glucose", "body_temperature", "sleep_hours", "mood"], index=0)
        window = st.selectbox("Window", [7, 14, 30], index=1)
        cutoff = datetime.utcnow() - timedelta(days=window)
        rows = session.query(HealthMeasurement).filter_by(metric_name=metric).filter(HealthMeasurement.timestamp >= cutoff).order_by(HealthMeasurement.timestamp.asc()).all()

        if rows:
            df = pd.DataFrame([
                {"timestamp": row.timestamp, "value": row.value, "source": row.source} for row in rows
            ])
            fig = px.line(df, x="timestamp", y="value", markers=True, line_shape="spline", color_discrete_sequence=["#9B7BFF"])
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                font=dict(color="#F4F3FF"),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data available for the selected signal in this time window.")

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='section-tag'>Alerts & observations</div>", unsafe_allow_html=True)
            if anomalies:
                for alert in anomalies:
                    st.warning(f"{alert.metric_name.upper()} • {alert.flag_level} • {alert.explanation}")
            else:
                st.success("No active anomaly flags in the current review window.")
            if latest_checkin is None:
                st.info("Pending daily check-in for current mission day.")
        with col2:
            st.markdown("<div class='section-tag'>Mission context</div>", unsafe_allow_html=True)
            if summary["latest_context"]:
                ctx = summary["latest_context"]
                st.markdown(
                    f"""
                    <div class='panel'>
                        <div style='color: var(--muted); font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;'>Phase</div>
                        <div style='font-size: 1.1rem; font-weight: 700; margin-top: 0.3rem;'>{ctx.phase}</div>
                        <div style='margin-top: 0.8rem; color: var(--muted);'>Recent activity: {ctx.recent_physical_activity}</div>
                        <div style='margin-top: 0.5rem; color: var(--muted);'>Nutrition: {ctx.nutrition}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("No mission context logged for current period.")

            if latest_checkin:
                st.markdown(
                    f"""
                    <div class='panel' style='margin-top: 0.8rem;'>
                        <div style='color: var(--muted); font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;'>Latest check-in</div>
                        <div style='margin-top: 0.45rem;'>Sleep: {latest_checkin.sleep_duration_hours} h</div>
                        <div>Mood: {latest_checkin.mood}/100</div>
                        <div>Energy: {latest_checkin.energy}/100</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    finally:
        session.close()
