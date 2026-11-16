"""Central provenance contract. Capture is transport evidence, never certification."""
import json
from collections import Counter
from database.models import MeasurementOrigin,MeasurementProvenance,MeasurementRevision,HealthMeasurement

CLASSES=('VERIFIED_DEVICE_CAPTURE','IMPORTED_EXTERNAL_DATA','NASA_PUBLIC_RESEARCH_DATA',
         'MANUALLY_ENTERED_DATA','SYNTHETIC_SIMULATION_DATA','UNKNOWN_UNVERIFIED')
DECLARED={'IMPORTED_DATA':'IMPORTED_EXTERNAL_DATA','MANUAL_INPUT':'MANUALLY_ENTERED_DATA',
          'MANUALLY_ENTERED_DATA':'MANUALLY_ENTERED_DATA','SIMULATED_DATA':'SYNTHETIC_SIMULATION_DATA'}
BOUNDARY='VERIFIED means recorded transport capture only; device identity, calibration and biomedical accuracy are not certified. HARDWARE NOT VALIDATED.'


def create_origin(session,row,proof):
    from utils.timestamps import utc_now
    classification=DECLARED.get(row.source,'UNKNOWN_UNVERIFIED')
    if row.source=='IMPORTED_DATA' and proof.connector not in {'authorized-folder','authorized-api','uploaded-csv'}:classification='UNKNOWN_UNVERIFIED'
    if row.source=='REAL_SENSOR_DATA' and proof.capture_verified and proof.connector=='ble-hrs':classification='VERIFIED_DEVICE_CAPTURE'
    origin=MeasurementOrigin(measurement_id=row.id,received_at=utc_now(),declared_source=row.source,
        classification=classification,device_id=proof.instrument if proof.connector=='ble-hrs' else None,
        batch_id=proof.receipt,acquisition_method=proof.connector,validation_status='SCHEMA_VALIDATED_NOT_CLINICAL',
        is_simulation=row.source=='SIMULATED_DATA',evidence_json=json.dumps({'capture_verified_at_receipt':proof.capture_verified,
            'instrument_declared':proof.instrument,'hardware_validated':False,'identity_authenticated':False,
            'evidence':json.loads(proof.details or '{}')},sort_keys=True))
    session.add(origin)


def describe(row,origin=None,proof=None):
    classification=origin.classification if origin else 'UNKNOWN_UNVERIFIED'
    # An envelope without the original capture evidence cannot assert verification.
    if classification=='VERIFIED_DEVICE_CAPTURE' and (proof is None or not proof.capture_verified):classification='UNKNOWN_UNVERIFIED'
    return dict(provenance_class=classification,received_at=origin.received_at if origin else None,
        device_id=origin.device_id if origin else None,batch_id=origin.batch_id if origin else None,
        acquisition_method=origin.acquisition_method if origin else 'unknown legacy acquisition',
        validation_status=origin.validation_status if origin else 'NO_PROVENANCE_EVIDENCE',
        is_simulation=row.source=='SIMULATED_DATA',declared_source=row.source,
        provenance_evidence=origin.evidence_json if origin else json.dumps({'legacy_capture_record':json.loads(proof.details or '{}'),
            'legacy_capture_claim':proof.capture_verified,'receipt':proof.receipt,'note':'Historical evidence retained without promoting current classification'} if proof else {}))


def profile_provenance(session,astronaut_id):
    rows=session.query(HealthMeasurement).filter_by(astronaut_id=astronaut_id).all()
    origins={r.measurement_id:r for r in session.query(MeasurementOrigin).join(HealthMeasurement).filter(HealthMeasurement.astronaut_id==astronaut_id)}
    proofs={r.measurement_id:r for r in session.query(MeasurementProvenance).join(HealthMeasurement).filter(HealthMeasurement.astronaut_id==astronaut_id)}
    revisions={}
    for revision in session.query(MeasurementRevision).filter_by(astronaut_id=astronaut_id).order_by(MeasurementRevision.id):
        revisions.setdefault(revision.measurement_id,[]).append(dict(id=revision.id,actor=revision.actor,reason=revision.reason,
            timestamp=str(revision.timestamp),before=json.loads(revision.before_json),after=json.loads(revision.after_json)))
    return [dict(measurement_id=r.id,astronaut_id=r.astronaut_id,metric_name=r.metric_name,value=r.value,unit=r.unit,
        measured_at=r.timestamp,quality=r.data_quality_status,**describe(r,origins.get(r.id),proofs.get(r.id)),
        revisions=revisions.get(r.id,[])) for r in rows]


def summary(session,astronaut_id):
    counts=Counter()
    for classification,captured in session.query(MeasurementOrigin.classification,MeasurementProvenance.capture_verified).select_from(HealthMeasurement).outerjoin(MeasurementOrigin).outerjoin(MeasurementProvenance).filter(HealthMeasurement.astronaut_id==astronaut_id):
        kind=classification or 'UNKNOWN_UNVERIFIED'
        if kind=='VERIFIED_DEVICE_CAPTURE' and not captured:kind='UNKNOWN_UNVERIFIED'
        counts[kind]+=1
    return dict(counts)
