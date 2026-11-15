from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics.anomaly import detect_anomalies
from analytics.eda import summarize_dataframe
from analytics.predictive import assess_prediction_readiness, build_demo_regression
from database.database import SessionLocal
from database.repository import get_analysis_records, get_imported_datasets, get_report_documents, seed_nasa_studies
from modules.nasa_data_hub.nasa_data_hub import render_nasa_data_hub
from modules.ui.theme import apply_theia_theme, render_page_header


def _build_demo_dataset() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=30, freq="D"),
            "heart_rate": [64, 66, 65, 68, 70, 71, 69, 72, 74, 73, 68, 67, 65, 66, 71, 75, 78, 77, 73, 70, 68, 69, 71, 72, 74, 76, 79, 77, 75, 73],
            "sleep_hours": [7.1, 7.4, 7.3, 6.9, 7.0, 7.2, 7.5, 6.6, 6.8, 7.0, 7.1, 7.4, 6.9, 7.5, 7.2, 6.8, 6.7, 7.0, 7.1, 7.2, 6.9, 7.0, 7.3, 7.1, 6.8, 6.7, 7.1, 7.4, 7.2, 7.0],
            "fatigue": [30, 34, 33, 35, 42, 39, 36, 42, 46, 48, 43, 38, 35, 31, 34, 40, 48, 52, 49, 43, 41, 37, 35, 38, 44, 47, 50, 49, 45, 42],
            "mood": [80, 78, 79, 76, 73, 75, 74, 71, 66, 69, 73, 76, 78, 80, 77, 72, 68, 67, 70, 74, 76, 78, 80, 77, 74, 71, 68, 69, 73, 75],
        }
    )


def render_intelligence_center() -> None:
    apply_theia_theme()
    render_page_header("THEIA Intelligence Center", "NASA evidence • analytics laboratory • predictive research • scientific reporting")

    session = SessionLocal()
    try:
        studies = seed_nasa_studies(session)
        analysis_records = get_analysis_records(session)
        imported_sets = get_imported_datasets(session)
        reports = get_report_documents(session)
    finally:
        session.close()

    tabs = st.tabs(["NASA Data Hub", "Analytics Laboratory", "Predictive Research", "Scientific Reports"])

    with tabs[0]:
        render_nasa_data_hub()

    with tabs[1]:
        demo_df = _build_demo_dataset()
        summary = summarize_dataframe(demo_df)
        st.subheader("Exploratory data analysis")
        st.write(summary["rows"], "rows")
        st.json({
            "missing_values": summary["missing_values"],
            "duplicate_rows": summary["duplicate_rows"],
            "numeric_columns": summary["numeric_columns"],
        })

        if "heart_rate" in demo_df.columns:
            anomaly_results = detect_anomalies(demo_df, value_col="heart_rate")
            st.write("Anomaly review")
            st.json(anomaly_results)

    with tabs[2]:
        prediction_df = _build_demo_dataset()
        readiness = assess_prediction_readiness(prediction_df, "fatigue", ["sleep_hours", "heart_rate", "mood"]) 
        st.json(readiness)
        if readiness["status"] == "ready_for_experiment":
            st.json(build_demo_regression(prediction_df, "fatigue", ["sleep_hours", "heart_rate", "mood"]))
        else:
            st.info("This experimental prediction path is educational and intentionally conservative until the dataset is adequate for a valid evaluation.")

    with tabs[3]:
        st.subheader("Scientific records")
        if studies:
            st.write(f"Catalogued NASA studies: {len(studies)}")
        if imported_sets:
            st.write(f"Imported datasets: {len(imported_sets)}")
        if analysis_records:
            st.json([{
                "analysis_type": item.analysis_type,
                "model_name": item.model_name,
                "result_summary": item.result_summary,
                "confidence": item.confidence,
            } for item in analysis_records[:5]])
        else:
            st.info("No analysis records have been generated yet.")

        if reports:
            st.write("Recent reports")
            for item in reports[:5]:
                st.caption(f"{item.report_type} • {item.title} • {item.generated_at.strftime('%Y-%m-%d')}" )
        else:
            st.info("No PDF or scientific report documents have been generated yet.")

        st.caption("All predictive and scientific outputs in THEIA are labeled as experimental and must be interpreted with mission context, not as certified medical advice.")
