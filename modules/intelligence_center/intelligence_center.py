import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut, get_report_documents
from intelligence.engine import analyze
from services.analysis_views import render_analysis
from utils.measurement_schema import ALLOWED_METRICS
from modules.ui.theme import apply_theia_theme, render_page_header


def render_intelligence_center():
    apply_theia_theme()
    render_page_header("THEIA Intelligence Center", "Shared statistical engine | Reproducible SQLite snapshots")
    with SessionLocal() as session:
        astronaut = ensure_astronaut(session)
        result = analyze(session, astronaut.id)
        st.json({"snapshot": result["fingerprint"], "quality": result["quality"], "period": result["period"]})
        metric = st.selectbox("Analysis indicator", sorted(ALLOWED_METRICS), key="intelligence_metric")
        render_analysis(session, astronaut.id, metric, "intelligence")
        st.subheader("Exploratory relationships")
        if result["relationships"]:
            st.dataframe(result["relationships"], hide_index=True)
        else:
            st.info("At least five paired UTC days with variable values are required. No relationship is inferred from unpaired data.")
        st.caption("No predictive clinical model is trained or validated by this workflow.")
        st.subheader("Report registry")
        for record in get_report_documents(session)[:5]:
            st.write(record.title, record.generated_at)

        if st.toggle("Open predictive research experiment", key="predictive_research"):
            from database.measurements import measurement_frame
            from analytics.predictive import build_demo_regression
            frame = measurement_frame(session, astronaut.id)
            frame = frame[(frame.data_quality_status == 'VALID') & frame.source.isin(['MANUAL_INPUT', 'MANUALLY_ENTERED_DATA', 'REAL_SENSOR_DATA'])].copy()
            if frame.empty:
                st.info("No validated mission observations for this experiment.")
            else:
                frame['day'] = frame.timestamp.dt.floor('D')
                daily = frame.pivot_table(index='day', columns='metric_name', values='value', aggfunc='mean')
                target = st.selectbox("Experimental target", daily.columns.tolist(), key="prediction_target")
                features = st.multiselect("Experimental predictors", [c for c in daily.columns if c != target], key="prediction_features")
                if st.button("Run educational regression", key="run_regression"):
                    st.json(build_demo_regression(daily, target, features))
                st.caption("Exploratory held-out random split, not a prospective time-series validation or a medical forecast.")
