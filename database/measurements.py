"""Shared validated measurement access. Times are stored as naive UTC."""
from datetime import datetime, timezone
import hashlib

import pandas as pd
from sqlalchemy.exc import IntegrityError

from database.models import AstronautProfile, HealthMeasurement
from utils.measurement_schema import MeasurementPayload


def query_measurements(session, astronaut_id, metric=None, start=None, end=None):
    start = start.astimezone(timezone.utc).replace(tzinfo=None) if start is not None and start.tzinfo else start
    end = end.astimezone(timezone.utc).replace(tzinfo=None) if end is not None and end.tzinfo else end
    if start is not None and end is not None and start > end:
        raise ValueError("Period start must be before its end")
    query = session.query(HealthMeasurement).filter_by(astronaut_id=astronaut_id)
    if metric:
        query = query.filter_by(metric_name=metric)
    if start is not None:
        query = query.filter(HealthMeasurement.timestamp >= start)
    if end is not None:
        query = query.filter(HealthMeasurement.timestamp <= end)
    return query.order_by(HealthMeasurement.timestamp, HealthMeasurement.id)


def measurement_frame(session, astronaut_id, metric=None, start=None, end=None):
    rows = query_measurements(session, astronaut_id, metric, start, end).all()
    columns = ["id", "metric_name", "value", "unit", "timestamp", "source", "data_quality_status", "mission_context"]
    return pd.DataFrame([{key: getattr(row, key) for key in columns} for row in rows], columns=columns)


def insert_measurement(session, astronaut_id, payload, commit=True):
    payload = payload if isinstance(payload, MeasurementPayload) else MeasurementPayload.model_validate(payload)
    if session.info.get('scenario'):
        payload = MeasurementPayload.model_validate(payload.model_dump() | {'source':'SIMULATED_DATA'})
    if session.get(AstronautProfile, astronaut_id) is None:
        raise ValueError("Astronaut profile does not exist")
    existing = query_measurements(session, astronaut_id, payload.metric_name).filter_by(timestamp=payload.timestamp).first()
    if existing:
        if existing.value != payload.value or existing.unit != payload.unit or existing.source != payload.source:
            raise ValueError("Conflicting measurement at the same timestamp; edit the existing record")
        return existing
    identity = hashlib.sha256(f"{astronaut_id}:{payload.metric_name}:{payload.timestamp.isoformat()}".encode()).hexdigest()
    record = HealthMeasurement(astronaut_id=astronaut_id, identity_key=identity, **payload.model_dump())
    connection = session.connection()
    if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql('BEGIN')
    try:
        with session.begin_nested():
            session.add(record)
            session.flush()
    except IntegrityError:
        existing = query_measurements(session, astronaut_id, payload.metric_name).filter_by(timestamp=payload.timestamp).first()
        if existing is None or existing.value != payload.value or existing.unit != payload.unit or existing.source != payload.source:
            raise ValueError("Conflicting concurrent measurement")
        record = existing
    if commit:
        session.commit()
    return record


def update_measurement(session, astronaut_id, record_id, changes):
    row = query_measurements(session, astronaut_id).filter_by(id=record_id).one()
    data = {key: getattr(row, key) for key in MeasurementPayload.model_fields}
    data.update(changes)
    payload = MeasurementPayload.model_validate(data)
    conflict = query_measurements(session, astronaut_id, payload.metric_name).filter_by(timestamp=payload.timestamp).filter(HealthMeasurement.id != record_id).first()
    if conflict:
        raise ValueError("Another measurement already exists at that timestamp")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.identity_key = hashlib.sha256(f"{astronaut_id}:{payload.metric_name}:{payload.timestamp.isoformat()}".encode()).hexdigest()
    session.commit()
    return row
