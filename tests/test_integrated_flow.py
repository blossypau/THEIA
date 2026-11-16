from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import numpy as np
import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.database import Base
from database.models import AstronautProfile, HealthMeasurement, ScientificAnalysisRecord
from database.measurements import insert_measurement, update_measurement, measurement_frame
from database.repository import ensure_astronaut, get_dashboard_summary
from intelligence.engine import analyze
from services.analysis_views import metric_view
from services.anatomy import anatomy_view, structure_registry
from services.datasets import register_table
from integrations.csv_import import import_csv
from modules.reports.reports import generate_pdf_report
from utils.measurement_schema import MeasurementPayload

@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'flow.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


def payload(value=70, day=0, metric='heart_rate', source='MANUALLY_ENTERED_DATA'):
    return dict(metric_name=metric, value=value, unit='bpm' if metric == 'heart_rate' else 'hours', timestamp=datetime(2026,1,1)+timedelta(days=day), source=source)


def test_registration_sqlite_dataframe_analysis_dashboard_anatomy_pdf(session, tmp_path):
    astronaut = ensure_astronaut(session)
    astronaut.name = "Synthetic integration test profile"
    session.commit()
    for day in range(25):
        insert_measurement(session, astronaut.id, payload(64 + day % 3 if day < 24 else 160, day))
        insert_measurement(session, astronaut.id, payload(7 + day % 3 / 10, day, 'sleep_hours'))
    snapshot = analyze(session, astronaut.id)
    assert len(measurement_frame(session, astronaut.id)) == 50
    assert snapshot['metrics']['heart_rate:mission']['samples'] == 25
    assert snapshot['metrics']['heart_rate:mission']['anomalies'][-1]['value'] == 160
    assert snapshot['relationships'][0]['paired_days'] == 25
    assert get_dashboard_summary(session)['analysis'] == snapshot
    assert metric_view(session, astronaut.id, 'heart_rate')['analysis'] == snapshot
    identifier = next(iter(structure_registry()))
    anatomy = anatomy_view(session, astronaut.id, identifier)
    assert anatomy['analysis'] == snapshot
    report = generate_pdf_report(session, tmp_path / 'flow.pdf')
    text = '\n'.join(page.extract_text() for page in PdfReader(report).pages)
    assert snapshot['fingerprint'] in text
    assert '160.000' in text and 'NASA' in text and 'Standard deviation' in text
    assert session.query(ScientificAnalysisRecord).filter_by(analysis_type='integrated_health').count() == 1
    Path('tmp/pdfs').mkdir(parents=True, exist_ok=True)
    Path('tmp/pdfs/integration.pdf').write_bytes(report.read_bytes())


def test_duplicates_conflicts_and_edits_invalidate_analysis(session):
    astronaut = ensure_astronaut(session)
    record = insert_measurement(session, astronaut.id, payload())
    assert insert_measurement(session, astronaut.id, payload()).id == record.id
    with pytest.raises(ValueError, match='Conflicting'):
        insert_measurement(session, astronaut.id, payload(71))
    old = analyze(session, astronaut.id)
    update_measurement(session, astronaut.id, record.id, {'value': 80})
    new = analyze(session, astronaut.id)
    assert old['fingerprint'] != new['fingerprint']
    assert new['metrics']['heart_rate:mission']['mean'] == 80
    assert session.query(ScientificAnalysisRecord).count() == 2


def test_profile_period_and_source_isolation(session):
    a = ensure_astronaut(session)
    b = AstronautProfile(name='Other',mission_id='OTHER');session.add(b);session.commit()
    insert_measurement(session, a.id, payload(65))
    insert_measurement(session, a.id, payload(170,1,source='SIMULATED_DATA'))
    insert_measurement(session, b.id, payload(200))
    result = analyze(session,a.id)
    assert result['metrics']['heart_rate:mission']['mean'] == 65
    assert result['metrics']['heart_rate:simulated']['mean'] == 170
    assert len(measurement_frame(session,a.id,end=datetime(2026,1,1))) == 1
    assert get_dashboard_summary(session)['latest_measurements'][0].astronaut_id == a.id


def test_invalid_values_time_units_and_zero():
    for changes in [{'value':float('nan')},{'value':float('inf')},{'unit':'hours'},{'timestamp':datetime.now(timezone.utc)+timedelta(days=1)}]:
        with pytest.raises(ValueError):
            MeasurementPayload.model_validate(payload() | changes)
    valid=MeasurementPayload.model_validate(payload(0,metric='sleep_hours'))
    assert valid.value == 0
    aware=MeasurementPayload.model_validate(payload() | {'timestamp':'2026-01-01T02:00:00+02:00'})
    assert aware.timestamp == datetime(2026,1,1)


def test_atomic_csv_and_idempotent_import(session):
    astronaut=ensure_astronaut(session)
    invalid=b'metric_name,value,unit,timestamp\nheart_rate,70,bpm,2026-01-01\nheart_rate,999,bpm,2026-01-02\n'
    with pytest.raises(ValueError): import_csv(session,io.BytesIO(invalid),astronaut.id)
    assert session.query(HealthMeasurement).count() == 0
    valid=invalid.replace(b'999',b'71')
    import_csv(session,io.BytesIO(valid),astronaut.id)
    import_csv(session,io.BytesIO(valid),astronaut.id)
    assert session.query(HealthMeasurement).count() == 2
    assert {r.source for r in session.query(HealthMeasurement)} == {'IMPORTED_DATA'}


def test_dataset_provenance_and_path_safety(session):
    a,frame=register_table(session,b'variable,value\nsleep,7\nfatigue,4\n','../../escape.csv','https://example.org/study')
    b,_=register_table(session,b'variable,value\nsleep,7\nfatigue,4\n','again.csv')
    assert a.id == b.id and a.file_name == 'escape.csv'
    assert a.source_label == 'IMPORTED_EXTERNAL_DATA'  # A declared HTTPS URL is not proof of public/NASA origin.
    assert len(frame) == 2


def test_empty_insufficient_constant_and_unknown_anatomy(session,tmp_path):
    astronaut=ensure_astronaut(session)
    empty=analyze(session,astronaut.id)
    assert empty['metrics'] == {} and empty['relationships'] == []
    for day in range(5): insert_measurement(session,astronaut.id,payload(70,day))
    result=analyze(session,astronaut.id)
    assert result['metrics']['heart_rate:mission']['std'] == 0
    assert result['metrics']['heart_rate:mission']['anomalies'] == []
    with pytest.raises(ValueError): anatomy_view(session,astronaut.id,'invented_heart')


def test_conflicting_csv_rolls_back_entire_batch(session):
    astronaut=ensure_astronaut(session)
    insert_measurement(session,astronaut.id,payload(70,1,source='IMPORTED_DATA'))
    content=b'metric_name,value,unit,timestamp\nheart_rate,75,bpm,2026-01-01\nheart_rate,99,bpm,2026-01-02\n'
    with pytest.raises(ValueError): import_csv(session,io.BytesIO(content),astronaut.id)
    assert session.query(HealthMeasurement).count() == 1


def test_low_variability_skips_isolation_forest(session):
    astronaut=ensure_astronaut(session)
    for day in range(25):insert_measurement(session,astronaut.id,payload(65+day%3,day))
    item=analyze(session,astronaut.id)['metrics']['heart_rate:mission']
    assert item['isolation_forest_status'] == 'insufficient_or_low_variability'
    assert item['anomalies'] == []


def test_backup_before_legacy_migration(tmp_path,monkeypatch):
    import database.database as database
    from sqlalchemy import text, inspect
    legacy_path=tmp_path/'legacy.db'
    legacy_engine=create_engine(f'sqlite:///{legacy_path}')
    with legacy_engine.begin() as connection:
        connection.execute(text('CREATE TABLE health_measurements (id INTEGER PRIMARY KEY, astronaut_id INTEGER, metric_name VARCHAR, value FLOAT, unit VARCHAR, timestamp DATETIME, source VARCHAR, data_quality_status VARCHAR, mission_context VARCHAR, notes TEXT)'))
        connection.execute(text("INSERT INTO health_measurements(id,metric_name,value) VALUES (1,'heart_rate',70)"))
    monkeypatch.setattr(database,'engine',legacy_engine)
    monkeypatch.setattr(database,'DB_PATH',legacy_path)
    database.init_db()
    assert 'identity_key' in {c['name'] for c in inspect(legacy_engine).get_columns('health_measurements')}
    with legacy_engine.connect() as connection:
        assert connection.execute(text('SELECT value FROM health_measurements WHERE id=1')).scalar() == 70
    backups=list((tmp_path/'data/backups').glob('*.sqlite3'))
    assert len(backups) == 1
    import sqlite3
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute('SELECT value FROM health_measurements').fetchone()[0] == 70
    legacy_engine.dispose()


def test_prediction_rejects_leakage_and_sparse_rows():
    import pandas as pd
    from analytics.predictive import assess_prediction_readiness
    frame=pd.DataFrame({'heart_rate':range(30),'sleep_hours':[float('nan')]*29+[7]})
    assert assess_prediction_readiness(frame,'heart_rate',['heart_rate'])['status'] == 'insufficient_data'
    assert assess_prediction_readiness(frame,'heart_rate',['sleep_hours'])['status'] == 'insufficient_data'


def test_isolation_forest_runs_with_sufficient_distinct_data(session):
    astronaut=ensure_astronaut(session)
    for day in range(25):insert_measurement(session,astronaut.id,payload(60+day/5 if day<24 else 150,day))
    item=analyze(session,astronaut.id)['metrics']['heart_rate:mission']
    assert item['isolation_forest_status'] == 'evaluated'
    assert any('isolation_forest' in flag['methods'] and flag['value']==150 for flag in item['anomalies'])
