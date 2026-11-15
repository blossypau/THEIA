from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from pydantic import ValidationError
from sqlalchemy import func

from database.database import SessionLocal
from database.models import HealthMeasurement
from utils.measurement_schema import MeasurementPayload


METRIC_OPTIONS = [
    "heart_rate",
    "blood_pressure",
    "blood_glucose",
    "body_temperature",
    "sleep_hours",
    "mood",
    "energy",
    "fatigue",
    "oxygen_saturation",
]


def _build_measurement_payload(form_data: dict) -> MeasurementPayload:
    payload = {
        "metric_name": form_data["metric_name"],
        "value": float(form_data["value"]),
        "unit": form_data["unit"],
        "timestamp": datetime.fromisoformat(form_data["timestamp"]),
        "source": form_data.get("source", "MANUALLY_ENTERED_DATA"),
        "data_quality_status": form_data.get("data_quality_status", "VALID"),
        "mission_context": form_data.get("mission_context"),
        "notes": form_data.get("notes"),
    }
    return MeasurementPayload.model_validate(payload)


def render_data_management() -> None:
    st.subheader("Health data management")
    st.caption("Validated measurements, persistent records, and CSV export for mission operations.")

    session = SessionLocal()
    try:
        with st.form("measurement_entry_form"):
            col1, col2 = st.columns(2)
            with col1:
                metric_name = st.selectbox("Metric", METRIC_OPTIONS)
                value = st.number_input("Value", min_value=0.0, step=0.1, format="%.2f")
                unit = st.selectbox(
                    "Unit",
                    ["bpm", "mmHg", "mg/dL", "C", "hours", "score", "%"],
                    index=0,
                )
            with col2:
                timestamp = st.datetime_input("Timestamp", value=datetime.utcnow())
                source = st.selectbox("Source", ["REAL_SENSOR_DATA", "MANUALLY_ENTERED_DATA", "SIMULATED_DATA", "PUBLIC_RESEARCH_DATA"])
                data_quality_status = st.selectbox("Data quality", ["VALID", "REVIEW", "MISSING", "INVALID"])
                mission_context = st.text_input("Mission context", value="Routine check")
            notes = st.text_area("Notes", placeholder="Optional context, observation, or sensor detail")
            submitted = st.form_submit_button("Save measurement")

        if submitted:
            payload = {
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "timestamp": timestamp.isoformat(),
                "source": source,
                "data_quality_status": data_quality_status,
                "mission_context": mission_context or None,
                "notes": notes or None,
            }

            try:
                validated = _build_measurement_payload(payload)
                record = HealthMeasurement(
                    astronaut_id=1,
                    metric_name=validated.metric_name,
                    value=float(validated.value),
                    unit=validated.unit,
                    timestamp=validated.timestamp,
                    source=validated.source,
                    data_quality_status=validated.data_quality_status,
                    mission_context=validated.mission_context,
                    notes=validated.notes,
                )
                session.add(record)
                session.commit()
                st.success(f"Measurement saved for {validated.metric_name}.")
            except ValidationError as exc:
                st.error(f"Validation failed: {exc}")

        st.markdown("---")
        metric_filter = st.selectbox("Filter by metric", ["All", *METRIC_OPTIONS], index=0)
        days = st.slider("Time window (days)", 1, 90, 30)
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = session.query(HealthMeasurement)
        if metric_filter != "All":
            query = query.filter_by(metric_name=metric_filter)
        query = query.filter(HealthMeasurement.timestamp >= cutoff).order_by(HealthMeasurement.timestamp.desc())
        rows = query.all()

        if rows:
            df = pd.DataFrame([
                {
                    "metric": row.metric_name,
                    "value": row.value,
                    "unit": row.unit,
                    "timestamp": row.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "source": row.source,
                    "quality": row.data_quality_status,
                    "context": row.mission_context,
                }
                for row in rows
            ])
            st.dataframe(df, use_container_width=True)

            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button("Export filtered records", csv_data, file_name="theia_measurements.csv", mime="text/csv")
        else:
            st.info("No measurements are available in the selected range.")

        quality_summary = session.query(
            HealthMeasurement.data_quality_status,
            func.count(HealthMeasurement.id),
        ).group_by(HealthMeasurement.data_quality_status).all()
        if quality_summary:
            st.markdown("<div class='section-tag'>Data quality snapshot</div>", unsafe_allow_html=True)
            quality_df = pd.DataFrame([
                {"status": row[0], "count": row[1]} for row in quality_summary
            ])
            st.bar_chart(quality_df.set_index("status")["count"])
    finally:
        session.close()
