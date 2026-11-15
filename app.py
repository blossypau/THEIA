from __future__ import annotations

from datetime import datetime

import streamlit as st
from sqlalchemy.orm import Session

from config.settings import APP_NAME, MISSION_ID
from database.database import SessionLocal, init_db
from database.repository import get_dashboard_summary, seed_sample_data
from modules.anomaly_detection.anomaly_detection import render_anomaly_detection
from modules.daily_checkin.daily_checkin import render_daily_checkin
from modules.dashboard.dashboard import render_dashboard
from modules.data_management.data_management import render_data_management
from modules.health_guidance.health_guidance import render_health_guidance
from modules.human_body.human_body import render_human_body
from modules.intelligence_center.intelligence_center import render_intelligence_center
from modules.mission_context.mission_context import render_mission_context
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
        seed_sample_data(session)
    finally:
        session.close()


def render_top_bar() -> None:
    session = SessionLocal()
    try:
        summary = get_dashboard_summary(session)
        astronaut = summary["astronaut"]
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        st.markdown(
            f"""
            <div class='mission-shell'>
                <div style='display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap;'>
                    <div>
                        <div class='section-tag'>ARCTURUS / Mission thread</div>
                        <div class='mission-title' style='font-size:1.6rem; margin-bottom:0.2rem;'>{astronaut.name}</div>
                        <div class='mission-subtitle'>Mission {MISSION_ID} • Day {astronaut.mission_day} • Phase: Routine • Data sync nominal</div>
                    </div>
                    <div style='display:flex; flex-wrap:wrap; gap:0.7rem; align-items:center;'>
                        <span class='status-pill'>Connected</span>
                        <span style='color: var(--muted); font-size:0.8rem;'>{current_time}</span>
                        <span style='color: var(--muted); font-size:0.8rem;'>Crew: 6</span>
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
        st.markdown(
            """
            <div class='brand-shell'>
                <div class='brand-mark'>
                    <div class='brand-orbit'>✦</div>
                    <div class='brand-name'>THEIA</div>
                </div>
                <div class='status-pill'>Operational</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        session = SessionLocal()
        try:
            summary = get_dashboard_summary(session)
            astronaut = summary["astronaut"]
            st.markdown(
                f"""
                <div class='profile-quadrant'>
                    <div class='profile-label'>Astronaut</div>
                    <div class='profile-name'>{astronaut.name}</div>
                    <div class='mini-meta'>Mission {MISSION_ID}</div>
                    <div class='mini-meta'>Mission day {astronaut.mission_day}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        finally:
            session.close()

        pages = {
            "Mission Overview": "mission_overview",
            "Health Dashboard": "health_dashboard",
            "Data Management": "data_management",
            "Human Body Explorer": "human_body",
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
        selected = st.radio("Navigation", list(pages.keys()), label_visibility="collapsed")
        st.caption("v2.0.0 — mission intelligence interface")
        return pages[selected]


def render_settings() -> None:
    st.subheader("System settings")
    st.info("Mission configuration and display preferences are monitored in the local system state.")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Mission ID", MISSION_ID)
        st.metric("Connection", "Nominal")
    with col2:
        st.metric("Sync state", "Live")
        st.metric("Telemetry queue", "Stable")


def main() -> None:
    apply_theia_theme()
    init_application()
    page_key = render_sidebar()
    render_top_bar()

    pages = {
        "mission_overview": render_dashboard,
        "health_dashboard": render_dashboard,
        "data_management": render_data_management,
        "human_body": render_human_body,
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
