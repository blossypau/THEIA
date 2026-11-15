from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.orm import Session

from config.settings import APP_NAME, MISSION_ID, ROOT_DIR
from database.database import SessionLocal, init_db
from database.repository import get_dashboard_summary, seed_sample_data
from modules.anomaly_detection.anomaly_detection import render_anomaly_detection
from modules.daily_checkin.daily_checkin import render_daily_checkin
from modules.dashboard.dashboard import render_dashboard
from modules.gamification.gamification import render_gamification
from modules.health_guidance.health_guidance import render_health_guidance
from modules.human_body.human_body import render_human_body
from modules.mission_context.mission_context import render_mission_context
from modules.nutrition.nutrition import render_nutrition
from modules.offline.offline import render_offline
from modules.personal_baseline.personal_baseline import render_personal_baseline
from modules.reports.reports import render_reports
from modules.timeline.timeline import render_timeline


st.set_page_config(page_title=APP_NAME, page_icon="🛰️", layout="wide")


@st.cache_data
def load_health_rules():
    path = ROOT_DIR / "config" / "health_rules.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def init_application():
    init_db()
    session: Session = SessionLocal()
    try:
        seed_sample_data(session)
    finally:
        session.close()


def set_theme():
    st.markdown(
        """
        <style>
        :root {
          --bg: #07141f;
          --panel: #102133;
          --panel-2: #121f2d;
          --accent: #b08cff;
          --accent-2: #6fe7ff;
          --text: #edf5ff;
          --muted: #9bb0c5;
          --warning: #ffbd59;
          --success: #7ef0c1;
          --danger: #ff7f7f;
        }
        body { background: var(--bg); color: var(--text); }
        .stApp { background: linear-gradient(180deg, #07141f 0%, #0d1728 100%); }
        [data-testid="stSidebar"] { background: rgba(10, 17, 28, 0.94); }
        .stMetric { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 10px; }
        .block-container { padding-top: 1.5rem; }
        .kpi { font-size: 1.1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    st.sidebar.title("THEIA")
    st.sidebar.caption(f"Mission ID: {MISSION_ID}")
    pages = {
        "Overview": render_dashboard,
        "Human Body": render_human_body,
        "Timeline": render_timeline,
        "Daily Check-In": render_daily_checkin,
        "Mission Context": render_mission_context,
        "Personal Baseline": render_personal_baseline,
        "Anomaly Detection": render_anomaly_detection,
        "Health Guidance": render_health_guidance,
        "Nutrition": render_nutrition,
        "Gamification": render_gamification,
        "Reports": render_reports,
        "Offline Mode": render_offline,
    }
    selected = st.sidebar.radio("Navigation", list(pages.keys()))
    return pages[selected]


def render_home_header():
    st.title("🛰️ THEIA")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Mission ID", MISSION_ID)
    with col2:
        st.metric("Mission Day", 128)
    with col3:
        st.metric("Astronaut", "Astra Ren")
    st.caption("Experimental astronaut health intelligence platform for long-duration missions.")


def main():
    set_theme()
    init_application()
    render_home_header()
    page = render_sidebar()
    page()


if __name__ == "__main__":
    main()
