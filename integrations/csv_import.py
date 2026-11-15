"""Atomic, validated CSV measurement import."""
import pandas as pd
from database.measurements import insert_measurement
from utils.measurement_schema import MeasurementPayload


def import_csv(session, csv_path, astronaut_id=1):
    frame = pd.read_csv(csv_path, sep=None, engine="python")
    required = {"metric_name", "value", "unit", "timestamp"}
    if not required.issubset(frame.columns) or frame.empty or len(frame) > 100000:
        raise ValueError("CSV requires metric_name, value, unit, timestamp and 1-100000 rows")
    payloads = []
    for index, row in frame.iterrows():
        data = {key: value for key, value in row.to_dict().items() if key in MeasurementPayload.model_fields and pd.notna(value)}
        data["source"] = "SIMULATED_DATA" if data.get("source") == "SIMULATED_DATA" else "IMPORTED_DATA"
        try:
            payloads.append(MeasurementPayload.model_validate(data))
        except ValueError as exc:
            raise ValueError(f"CSV row {index + 2}: {exc}") from exc
    try:
        records = [insert_measurement(session, astronaut_id, payload, commit=False) for payload in payloads]
        session.commit()
        return records
    except Exception:
        session.rollback()
        raise
