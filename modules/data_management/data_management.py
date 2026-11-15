import streamlit as st
from datetime import datetime, timezone
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from database.database import SessionLocal
from database.repository import ensure_astronaut
from database.measurements import insert_measurement, measurement_frame, update_measurement
from integrations.csv_import import import_csv
from utils.measurement_schema import MeasurementPayload, UNIT_BY_METRIC, ALLOWED_SOURCES


def _build_measurement_payload(form_data):
    return MeasurementPayload.model_validate(form_data)


def render_data_management():
    st.caption("Health data management workspace")
    st.caption("Timestamps use UTC. Mood, energy and fatigue use a 0-100 score. Blood pressure is a single recorded pressure value; record its context explicitly.")
    with SessionLocal() as session:
        astronaut = ensure_astronaut(session)
        metric = st.selectbox("Metric", sorted(UNIT_BY_METRIC), key="entry_metric")
        unit = sorted(UNIT_BY_METRIC[metric])[0]
        with st.form("measurement_entry_form"):
            value = st.number_input(f"Value ({unit})", min_value=0.0, step=0.1, key="entry_value")
            timestamp = st.datetime_input("Timestamp (UTC)", value=datetime.now(timezone.utc).replace(tzinfo=None), key="entry_timestamp")
            source = st.selectbox("Source", ["MANUALLY_ENTERED_DATA", "SIMULATED_DATA", "REAL_SENSOR_DATA"], key="entry_source")
            context = st.text_input("Mission context", key="entry_context")
            notes = st.text_area("Notes", key="entry_notes")
            submitted = st.form_submit_button("Save measurement", key="save_measurement")
        if submitted:
            try:
                row = insert_measurement(session, astronaut.id, dict(metric_name=metric, value=value, unit=unit, timestamp=timestamp, source=source, mission_context=context, notes=notes))
                st.success(f"Measurement {row.id} saved (an identical timestamp returns the existing record).")
            except (ValueError, SQLAlchemyError) as exc:
                session.rollback()
                st.error(f"Could not save: {exc}")
        uploaded = st.file_uploader("Import measurements CSV", type=["csv"], key="measurements_csv")
        if uploaded and st.button("Validate and import measurements", key="import_measurements"):
            try:
                records = import_csv(session, uploaded, astronaut.id)
                st.success(f"Validated {len(records)} rows. Research imports are labeled IMPORTED_DATA.")
            except (ValueError, SQLAlchemyError) as exc:
                session.rollback()
                st.error(str(exc))
        frame = measurement_frame(session, astronaut.id)
        if frame.empty:
            st.info("No measurements yet.")
            return
        selected = st.selectbox("Filter by metric", ["All", *sorted(frame.metric_name.unique())], key="data_metric")
        period = st.date_input("Period (UTC)", value=(frame.timestamp.min().date(), frame.timestamp.max().date()), key="data_period")
        if len(period) != 2:
            st.info("Select both dates for the period.")
            return
        frame = frame[(frame.timestamp.dt.date >= period[0]) & (frame.timestamp.dt.date <= period[1])]
        filtered = frame if selected == "All" else frame[frame.metric_name == selected]
        st.dataframe(filtered, hide_index=True)
        st.download_button("Export filtered records", filtered.to_csv(index=False), "theia_measurements.csv", "text/csv")
        with st.expander("Correct an existing measurement"):
            record_id = st.selectbox("Record ID", frame.id.tolist(), key="edit_record")
            corrected = st.number_input("Corrected value", min_value=0.0, value=float(frame.loc[frame.id == record_id, "value"].iloc[0]), key=f"corrected_{record_id}")
            if st.button("Save correction", key="save_correction"):
                try:
                    update_measurement(session, astronaut.id, record_id, {"value": corrected})
                    st.success("Correction saved. Derived analysis will be recomputed on the next view.")
                    st.rerun()
                except (ValueError, SQLAlchemyError) as exc:
                    session.rollback()
                    st.error(str(exc))
