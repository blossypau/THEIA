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


st.set_page_config(page_title="THEIA | Space Health Command", page_icon=":material/hub:", layout="wide")
from html import escape
from database.models import AstronautProfile
from database.repository import active_astronaut_id
from modules.ui.theme import render_page_header

PAGES = {
    "Mission Overview": "mission_overview", "Scientific Analysis": "scientific_health", "Mission Scenario Mode": "scenario", "Health Dashboard": "health_dashboard",
    "Health Monitoring": "health_monitoring", "Data Management": "data_management",
    "Human Body Explorer": "human_body", "Medical Visualization Lab": "medical_visualization_lab",
    "NASA Data Hub": "nasa_data_hub", "THEIA Intelligence Center": "intelligence_center",
    "Mission Timeline": "timeline", "Daily Check-in": "daily_checkin", "Personal Baseline": "baseline",
    "Intelligent Analysis": "analysis", "Nutrition": "nutrition", "Health Guidance": "guidance",
    "Mission Reports": "reports", "Settings": "settings",
}


def init_application():
    if not st.session_state.get('scenario_mode'):
        init_db()
    with SessionLocal() as session:
        ensure_astronaut(session)


def _live_system_state(session):
    astronaut = ensure_astronaut(session)
    latest = session.query(HealthMeasurement).filter_by(astronaut_id=astronaut.id).order_by(HealthMeasurement.timestamp.desc()).first()
    context = session.query(MissionContext).filter_by(astronaut_id=astronaut.id).order_by(MissionContext.timestamp.desc()).first()
    return {"connection": "Local records" if latest else "No local data", "sync": "Local only",
            "phase": context.phase if context else "Unspecified", "last_measurement": str(latest.timestamp) if latest else "No measurements",
            "last_context": str(context.timestamp) if context else "No context recorded"}


def _profile_changed():
    st.session_state.pop('science_nn_result', None)
    st.session_state.pop('report_bytes', None)
    st.session_state.pop('report_profile_id', None)
    for key in list(st.session_state):
        if key.startswith('history_'):
            st.session_state.pop(key, None)


def _workspace_changed():
    _profile_changed()
    for key in ['active_astronaut','active_structure','last_anatomy_event','anatomy_structure','anatomy_command_revision','_anatomy_pending_sync','scenario_result','scenario_pdf_bytes','scenario_pdf_profile']:
        st.session_state.pop(key,None)


def render_sidebar():
    with st.sidebar:
        st.markdown("<div class='brand-shell'><div class='brand-mark'><div class='brand-orbit'>✧</div><div class='brand-name'>THEIA</div></div><div class='brand-caption'>SPACE HEALTH COMMAND CENTER</div></div>", unsafe_allow_html=True)
        st.toggle('Synthetic scenario workspace',key='scenario_mode',on_change=_workspace_changed,help='A separate SQLite database for this browser session. No real measurements are edited or reset.')
        with SessionLocal() as session:
            profiles = session.query(AstronautProfile).order_by(AstronautProfile.id).all()
            labels = {p.id: p.name for p in profiles}
            st.selectbox("Active astronaut", list(labels), format_func=lambda key: labels[key], key="active_astronaut", on_change=_profile_changed, help="Applies to all mission measurements, analyses, anatomy panels and reports.")
        st.caption("WORKSPACE / MISSION OPERATIONS")
        selected = st.radio("Navigation", list(PAGES), label_visibility="collapsed", key="navigation")
        st.divider()
        st.caption("THEIA 4.1 · LOCAL RESEARCH BUILD")
        st.caption("Experimental analytics. No remote synchronization inferred.")
        return PAGES[selected]


def render_top_bar():
    with SessionLocal() as session:
        astronaut = ensure_astronaut(session)
        state = _live_system_state(session)
        current = datetime.now(timezone.utc).strftime('%H:%M UTC')
        st.markdown(f"<div class='command-bar'><div class='command-identity'><span class='mission-code'>{escape(astronaut.mission_id)}</span><span class='command-title'>{escape(astronaut.name)} / Day {astronaut.mission_day:03}</span></div><div class='command-meta'>LOCAL STORAGE &nbsp; / &nbsp; {escape(state['last_measurement'])} &nbsp; / &nbsp; {current}</div></div>",unsafe_allow_html=True)


def render_settings():
    st.caption("Mission configuration and data provenance")
    with SessionLocal() as session:
        astronaut = ensure_astronaut(session)
        st.metric("Mission", astronaut.mission_id)
        st.metric("Selected profile", astronaut.name)
    st.info("Records stay in local SQLite. Sensor connectivity and remote sync are not implied by stored measurements.")
    if st.button("Load explicit synthetic demo", key="seed_demo"):
        with SessionLocal() as session:
            seed_sample_data(session)
        st.success("Synthetic demo loaded only if the database contained no measurements.")


def render_application():
    apply_theia_theme()
    init_application()
    page_key = render_sidebar()
    token = active_astronaut_id.set(st.session_state['active_astronaut'])
    try:
        render_top_bar()
        if st.session_state.get('scenario_mode'):
            st.warning('SYNTHETIC SCENARIO WORKSPACE · Isolated SQLite · All recorded measurements are simulated')
        from modules.dashboard.dashboard import render_health_dashboard
        from modules.scenario import render_scenario
        from modules.scientific_health import render_scientific_health
        pages = {"scientific_health": render_scientific_health, "scenario": render_scenario, "mission_overview": render_dashboard, "health_dashboard": render_health_dashboard,
            "health_monitoring": render_health_monitoring, "data_management": render_data_management,
            "human_body": render_human_body, "medical_visualization_lab": render_medical_visualization_lab,
            "nasa_data_hub": render_nasa_data_hub, "intelligence_center": render_intelligence_center,
            "timeline": render_timeline, "daily_checkin": render_daily_checkin, "baseline": render_personal_baseline,
            "analysis": render_anomaly_detection, "nutrition": render_nutrition, "guidance": render_health_guidance,
            "reports": render_reports, "settings": render_settings}
        generic = {"data_management", "baseline", "analysis", "reports", "settings", "guidance"}
        if page_key in generic:
            title = next(name for name,key in PAGES.items() if key==page_key)
            render_page_header(title, "Mission workspace / selected astronaut / local research records")
        pages[page_key]()
        st.markdown(f"<div class='workspace-footer'>THEIA / SPACE HEALTH COMMAND &nbsp; · &nbsp; {escape(st.session_state['navigation'])} &nbsp; · &nbsp; EXPERIMENTAL RESEARCH</div>",unsafe_allow_html=True)
    finally:
        active_astronaut_id.reset(token)


def main():
    from database.database import session_factory_override
    from uuid import uuid4
    factory = None
    if st.session_state.get('scenario_mode'):
        from services.scenario import scenario_factory
        if 'scenario_workspace_id' not in st.session_state:
            st.session_state['scenario_workspace_id'] = str(uuid4())
        factory = scenario_factory(st.session_state['scenario_workspace_id'])
    workspace_token = session_factory_override.set(factory)
    try:
        render_application()
    finally:
        session_factory_override.reset(workspace_token)


if __name__ == '__main__': main()
