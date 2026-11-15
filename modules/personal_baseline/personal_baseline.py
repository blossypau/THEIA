import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut
from services.analysis_views import render_analysis
from utils.measurement_schema import ALLOWED_METRICS


def render_personal_baseline():
    st.caption("Personal baseline workspace")
    metric = st.selectbox("Metric", sorted(ALLOWED_METRICS), key="baseline_metric")
    with SessionLocal() as session:
        render_analysis(session, ensure_astronaut(session).id, metric, "baseline")
