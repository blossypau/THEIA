import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut, get_dashboard_summary, get_mission_events
from services.analysis_views import render_analysis
from modules.ui.theme import apply_theia_theme, render_page_header
from utils.measurement_schema import ALLOWED_METRICS


def render_dashboard():
    apply_theia_theme()
    render_page_header("Mission overview", "THEIA 3.0 | Local mission records | Experimental analytics")
    with SessionLocal() as session:
        summary = get_dashboard_summary(session)
        astronaut = summary["astronaut"]
        analysis = summary["analysis"]
        st.caption(f"{astronaut.name} | Mission {astronaut.mission_id} | Day {astronaut.mission_day}")
        cols = st.columns(3)
        cols[0].metric("Stored measurements", analysis["quality"]["total"], border=True)
        cols[1].metric("Excluded from analysis", analysis["quality"]["excluded"], border=True)
        cols[2].metric("Statistical flags", sum(len(v["anomalies"]) for v in analysis["metrics"].values()), border=True)
        st.write("Recorded sources", analysis["quality"]["sources"])
        for row in summary["latest_measurements"]:
            with st.container(border=True):
                st.metric(row.metric_name.replace("_", " "), f"{row.value:g} {row.unit}")
                st.caption(f"{row.timestamp} UTC | {row.source} | {row.data_quality_status}")
        metric = st.selectbox("Indicator", sorted(ALLOWED_METRICS), key="dashboard_metric")
        render_analysis(session, astronaut.id, metric, "dashboard")
        st.subheader("Mission events")
        events = get_mission_events(session)
        if not events:
            st.info("No mission events recorded.")
        for event in events[-5:]:
            st.write(f"{event.timestamp} UTC - {event.event_type}: {event.description}")
        st.caption("Open Human Body Explorer or Mission Reports from navigation to inspect these same records.")
