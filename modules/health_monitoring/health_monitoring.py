from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.repository import get_dashboard_summary, get_measurements_for_metric, save_health_measurement
from modules.ui.theme import apply_theia_theme, render_page_header


METRIC_OPTIONS = [
    "heart_rate",
    "blood_pressure",
    "body_temperature",
    "sleep_hours",
    "mood",
    "oxygen_saturation",
    "blood_glucose",
    "fatigue",
]


def _format_delta(current: float, previous: float | None) -> str:
    if previous is None:
        return "Baseline unavailable"
    delta = current - previous
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2f} vs prior"


def render_health_monitoring() -> None:
    from modules.data_management.data_management import render_data_management
    from services.analysis_views import render_analysis
    from database.repository import ensure_astronaut
    apply_theia_theme()
    render_page_header("Health monitoring", "Validated entry and shared physiological analysis")
    render_data_management()
    metric = st.selectbox("Signal to inspect", METRIC_OPTIONS, key="monitoring_metric")
    with SessionLocal() as session:
        render_analysis(session, ensure_astronaut(session).id, metric, "monitoring")
