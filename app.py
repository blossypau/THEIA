from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import APP_NAME, MISSION_ID
from database.database import SessionLocal, init_db
from database.models import HealthMeasurement, MissionContext
from database.repository import get_dashboard_summary, ensure_astronaut, seed_sample_data
from modules.anomaly_detection.anomaly_detection import render_anomaly_detection
from modules.daily_checkin.daily_checkin import render_daily_checkin
from modules.dashboard.dashboard import render_dashboard
from modules.data_management.data_management import render_data_management
from modules.health_guidance.health_guidance import render_health_guidance
from modules.health_monitoring.health_monitoring import render_health_monitoring
from modules.human_body.human_body import render_human_body
from modules.intelligence_center.intelligence_center import render_intelligence_center
from modules.mission_context.mission_context import render_mission_context
from modules.medical_visualization_lab.medical_visualization_lab import render_medical_visualization_lab
from modules.nasa_data_hub.nasa_data_hub import render_nasa_data_hub
from modules.nutrition.nutrition import render_nutrition
from modules.personal_baseline.personal_baseline import render_personal_baseline
from modules.reports.reports import render_reports
from modules.timeline.timeline import render_timeline
from modules.ui.theme import apply_theia_theme

st.set_page_config(page_title=APP_NAME, page_icon="🛰️", layout="wide")


def init_application() -> None:
    init_db()
    session: Session = SessionLocal()
    try:
        ensure_astronaut(session)
    finally:
        session.close()


def _live_system_state(session: Session) -> dict[str, str]:
    measurement_count = session.query(func.count(HealthMeasurement.id)).scalar() or 0
    latest_measurement = session.query(HealthMeasurement.timestamp).order_by(HealthMeasurement.timestamp.desc()).first()
    latest_context = session.query(MissionContext.timestamp).order_by(MissionContext.timestamp.desc()).first()

    if measurement_count == 0:
        return {
            "connection": "No local data",
            "sync": "Idle",
            "phase": "Awaiting metrics",
            "last_measurement": "No recent measurements",
            "last_context": "No mission context",
        }

    last_measurement_time = latest_measurement[0] if latest_measurement else None
    last_context_time = latest_context[0] if latest_context else None
    phase = "Monitoring" if last_measurement_time else "Awaiting metrics"
    connection = "Local records" if last_measurement_time else "Limited"
    sync = "Local only" if last_measurement_time else "Idle"

    return {
        "connection": connection,
        "sync": sync,
        "phase": phase,
        "last_measurement": last_measurement_time.strftime("%Y-%m-%d %H:%M UTC") if last_measurement_time else "No recent measurements",
        "last_context": last_context_time.strftime("%Y-%m-%d %H:%M UTC") if last_context_time else "No mission context",
    }


def render_top_bar() -> None:
    session = SessionLocal()
    try:
        summary = get_dashboard_summary(session)
        astronaut = summary["astronaut"]
        state = _live_system_state(session)
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        st.markdown(
            f"""
            <div class='mission-shell'>
                <div style='display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap;'>
                    <div>
                        <div class='section-tag'>ARCTURUS / Mission thread</div>
                        <div class='mission-title' style='font-size:1.6rem; margin-bottom:0.2rem;'>{astronaut.name}</div>
                        <div class='mission-subtitle'>Mission {MISSION_ID} • Day {astronaut.mission_day} • Phase: {state['phase']} • Last measurement: {state['last_measurement']}</div>
                    </div>
                    <div style='display:flex; flex-wrap:wrap; gap:0.7rem; align-items:center;'>
                        <span class='status-pill'>{state['connection']}</span>
                        <span style='color: var(--muted); font-size:0.8rem;'>{current_time}</span>
                        <span style='color: var(--muted); font-size:0.8rem;'>Sync: {state['sync']}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    finally:
        session.close()


def render_sidebar() -> str:
    with st.sidebar:
        session = SessionLocal()
        try:
            summary = get_dashboard_summary(session)
            astronaut = summary["astronaut"]
            state = _live_system_state(session)
            st.markdown(
                f"""
                <div class='brand-shell'>
                    <div class='brand-mark'>
                        <div class='brand-orbit'>✦</div>
                        <div class='brand-name'>THEIA</div>
                    </div>
                    <div class='status-pill'>{state['sync']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class='profile-quadrant'>
                    <div class='profile-label'>Astronaut</div>
                    <div class='profile-name'>{astronaut.name}</div>
                    <div class='mini-meta'>Mission {MISSION_ID}</div>
                    <div class='mini-meta'>Mission day {astronaut.mission_day}</div>
                    <div class='mini-meta'>Last context: {state['last_context']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        finally:
            session.close()

        pages = {
            "Mission Overview": "mission_overview",
            "Health Dashboard": "health_dashboard",
            "Health Monitoring": "health_monitoring",
            "Data Management": "data_management",
            "Human Body Explorer": "human_body",
            "Medical Visualization Lab": "medical_visualization_lab",
            "NASA Data Hub": "nasa_data_hub",
            "THEIA Intelligence Center": "intelligence_center",
            "Mission Timeline": "timeline",
            "Daily Check-in": "daily_checkin",
            "Personal Baseline": "baseline",
            "Intelligent Analysis": "analysis",
            "Nutrition": "nutrition",
            "Health Guidance": "guidance",
            "Mission Reports": "reports",
            "Settings": "settings",
        }
        selected = st.radio("Navigation", list(pages.keys()), label_visibility="collapsed", key="navigation")
        st.caption("v3.0.0 — mission intelligence interface")
        return pages[selected]


def render_settings() -> None:
    st.subheader("System settings")
    st.caption("Local SQLite storage. No sensor connection or remote synchronization is inferred from stored records.")
    st.write(f"Mission: {MISSION_ID}")
    if st.button("Load explicit synthetic demo", key="seed_demo"):
        with SessionLocal() as session:
            seed_sample_data(session)
        st.success("Synthetic demo loaded only if the database contained no measurements.")


def main() -> None:
    apply_theia_theme()
    init_application()
    page_key = render_sidebar()
    render_top_bar()

    pages = {
        "mission_overview": render_dashboard,
        "health_dashboard": render_dashboard,
        "health_monitoring": render_health_monitoring,
        "data_management": render_data_management,
        "human_body": render_human_body,
        "medical_visualization_lab": render_medical_visualization_lab,
        "nasa_data_hub": render_nasa_data_hub,
        "intelligence_center": render_intelligence_center,
        "timeline": render_timeline,
        "daily_checkin": render_daily_checkin,
        "baseline": render_personal_baseline,
        "analysis": render_anomaly_detection,
        "nutrition": render_nutrition,
        "guidance": render_health_guidance,
        "reports": render_reports,
        "settings": render_settings,
    }

    pages[page_key]()


if __name__ == "__main__":
    main()
