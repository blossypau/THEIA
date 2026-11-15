import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut
from services.analysis_views import render_analysis
from utils.measurement_schema import ALLOWED_METRICS


def render_anomaly_detection():
    st.subheader("Intelligent analysis")
    metric = st.selectbox("Metric to inspect", sorted(ALLOWED_METRICS), key="anomaly_metric")
    with SessionLocal() as session:
        view = render_analysis(session, ensure_astronaut(session).id, metric, "anomaly")
        for item in view["baselines"]:
            st.write(f"{item['cohort']} | Isolation Forest: {item['isolation_forest_status']}")
            if item["anomalies"]:
                st.dataframe(item["anomalies"])
