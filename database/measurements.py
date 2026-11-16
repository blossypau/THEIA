"""Shared validated measurement access. Times are stored as naive UTC."""
from datetime import datetime, timezone
import hashlib
import json

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
    from services.provenance import describe
    from database.models import MeasurementOrigin,MeasurementProvenance
    origins={r.measurement_id:r for r in session.query(MeasurementOrigin).join(HealthMeasurement).filter(HealthMeasurement.astronaut_id==astronaut_id)}
    proofs={r.measurement_id:r for r in session.query(MeasurementProvenance).join(HealthMeasurement).filter(HealthMeasurement.astronaut_id==astronaut_id)}
    metadata=['provenance_class','received_at','device_id','batch_id','acquisition_method','validation_status','is_simulation','declared_source','provenance_evidence']
    return pd.DataFrame([{**{key: getattr(row, key) for key in columns},**describe(row,origins.get(row.id),proofs.get(row.id))} for row in rows],columns=columns+metadata)


def insert_measurement(session, astronaut_id, payload, commit=True):
    payload = payload if isinstance(payload, MeasurementPayload) else MeasurementPayload.model_validate(payload)
    if session.info.get('scenario'):
        payload = MeasurementPayload.model_validate(payload.model_dump() | {'source':'SIMULATED_DATA'})
    if payload.source == 'REAL_SENSOR_DATA' and not session.info.get('verified_sensor_capture'):
        raise ValueError('Sensor provenance requires an active acquisition connector; manual entry is not verified sensor capture')
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
            from database.models import MeasurementProvenance
            meta=session.info.get('acquisition_provenance',{})
            proof=MeasurementProvenance(measurement_id=record.id,connector=meta.get('connector','manual-or-legacy-api'),
                instrument=meta.get('instrument','Declared source; no device verified'),receipt=meta.get('receipt',identity),
                capture_verified=bool(session.info.get('verified_sensor_capture')),details=json.dumps(meta))
            session.add(proof)
            from services.provenance import create_origin
            create_origin(session,record,proof)
    except IntegrityError:
        existing = query_measurements(session, astronaut_id, payload.metric_name).filter_by(timestamp=payload.timestamp).first()
        if existing is None or existing.value != payload.value or existing.unit != payload.unit or existing.source != payload.source:
            raise ValueError("Conflicting concurrent measurement")
        record = existing
    if commit:
        session.commit()
    return record


def update_measurement(session, astronaut_id, record_id, changes, actor='local operator', reason='Manual correction'):
    row = query_measurements(session, astronaut_id).filter_by(id=record_id).one()
    data = {key: getattr(row, key) for key in MeasurementPayload.model_fields}
    captured_fields={key:data[key] for key in ('metric_name','value','unit','timestamp')}
    before=json.dumps(data,default=str,sort_keys=True)
    data.update(changes)
    payload = MeasurementPayload.model_validate(data)
    if payload.source != row.source:
        raise ValueError('A correction cannot relabel acquisition provenance')
    if not reason.strip() or not actor.strip():raise ValueError('Correction requires an actor and reason')
    conflict = query_measurements(session, astronaut_id, payload.metric_name).filter_by(timestamp=payload.timestamp).filter(HealthMeasurement.id != record_id).first()
    if conflict:
        raise ValueError("Another measurement already exists at that timestamp")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.identity_key = hashlib.sha256(f"{astronaut_id}:{payload.metric_name}:{payload.timestamp.isoformat()}".encode()).hexdigest()
    from database.models import MeasurementRevision,MeasurementProvenance
    proof=session.get(MeasurementProvenance,row.id)
    if proof is not None and proof.capture_verified and any(getattr(payload,key)!=value for key,value in captured_fields.items()):
        metadata=json.loads(proof.details or '{}')
        metadata.update(original_capture_verified=True,current_value_manually_corrected=True)
        proof.details=json.dumps(metadata);proof.capture_verified=False
        from database.models import MeasurementOrigin
        origin=session.get(MeasurementOrigin,row.id)
        if origin is not None:
            origin.classification='UNKNOWN_UNVERIFIED'
            evidence=json.loads(origin.evidence_json);evidence['current_value_manually_corrected']=True
            origin.evidence_json=json.dumps(evidence)
    session.add(MeasurementRevision(astronaut_id=astronaut_id,measurement_id=row.id,before_json=before,
        after_json=json.dumps(payload.model_dump(),default=str,sort_keys=True),actor=actor[:100],reason=reason))
    session.commit()
    return row
