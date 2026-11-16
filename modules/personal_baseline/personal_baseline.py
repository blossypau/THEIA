import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut
from services.analysis_views import render_analysis
from utils.measurement_schema import ALLOWED_METRICS


def render_personal_baseline():
    st.caption("Personal baseline workspace")
    metric = st.selectbox("Metric", sorted(ALLOWED_METRICS), index=sorted(ALLOWED_METRICS).index("heart_rate"), key="baseline_metric")
    with SessionLocal() as session:
        from modules.ui.explanations import render_historical
        render_historical(session,ensure_astronaut(session).id,metric)
        st.caption('Descriptive history below retains the old retrospective window statistics for compatibility; it is not the independent reference above.')
        render_analysis(session, ensure_astronaut(session).id, metric, "baseline")
