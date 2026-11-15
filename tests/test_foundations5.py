import asyncio
from datetime import datetime,timedelta
from pathlib import Path
from uuid import uuid4
import pytest
from database.models import AstronautProfile,HealthMeasurement,MeasurementRevision,MeasurementProvenance
from database.measurements import insert_measurement,update_measurement
from services.scenario import scenario_factory
from integrations.acquisition import SyntheticConnector,FolderConnector,Batch,ingest
from integrations.bluetooth_sensor import parse_heart_rate,BluetoothSensor
from intelligence.historical import historical_analysis


@pytest.fixture
def session(tmp_path):
    with scenario_factory(str(uuid4()),str(tmp_path))() as s:yield s


def test_historical_excludes_evaluated_and_future(session):
    insert_measurement(session,1,dict(metric_name='fatigue',value=80,unit='score',timestamp=datetime(2026,1,31),source='SIMULATED_DATA'))
    result=historical_analysis(session,1,start=datetime(2026,1,31))
    item=next(i for i in result['signals'] if i['metric']=='fatigue')
    assert item['samples']==30 and item['days']==30
    assert item['observations'][0]['flagged']
    assert item['observations'][0]['id'] not in item['reference_ids']
    assert historical_analysis(session,1,start=datetime(2026,1,31))==result


def test_correlations_keep_exact_sources_separate(session):
    from intelligence.engine import analyze
    session.info['scenario']=False
    for hour,source in enumerate(['MANUALLY_ENTERED_DATA','IMPORTED_DATA']):
        for day in range(6):
            for metric,value,unit in [('heart_rate',65+day,'bpm'),('fatigue',30+day,'score')]:
                insert_measurement(session,1,dict(metric_name=metric,value=value,unit=unit,
                    timestamp=datetime(2026,3,1,hour)+timedelta(days=day),source=source))
    relations=analyze(session,1,persist=False)['relationships']
    pairs=[r for r in relations if {r['left'],r['right']}=={'heart_rate','fatigue'} and r['source']!='SIMULATED_DATA']
    assert {r['source'] for r in pairs}=={'MANUALLY_ENTERED_DATA','IMPORTED_DATA'}
    assert all(r['paired_days']==6 for r in pairs)


def test_authorized_folder_stores_import_with_receipt(session,tmp_path):
    session.info['scenario']=False
    path=tmp_path/'authorized.csv'
    path.write_text('metric_name,value,unit,timestamp\nheart_rate,73,bpm,2026-03-01T08:00:00\n')
    connector=FolderConnector(tmp_path)
    assert connector.poll()==[]
    batch=connector.poll()[0]
    result=ingest(session,1,batch);connector.acknowledge(batch)
    assert result['source']=='IMPORTED_DATA' and not result['capture_verified']
    assert connector.poll()==[]
    assert path.exists() and session.get(MeasurementProvenance,result['measurement_ids'][0]).receipt==result['receipt']


def test_replay_controls_idempotence_and_provenance(session):
    replay=SyntheticConnector();replay.command('start');batches=replay.poll()
    first=ingest(session,1,batches[0]);second=ingest(session,1,batches[0])
    assert first==second and len(first['measurement_ids'])==5
    proof=session.get(MeasurementProvenance,first['measurement_ids'][0])
    assert proof.connector=='synthetic-replay' and not proof.capture_verified
    replay.command('pause');assert replay.poll()==[]
    replay.command('resume');assert replay.poll()
    replay.command('reset');assert replay.position==0 and replay.state=='STOPPED'


def test_revision_and_source_protection(session):
    row=session.query(HealthMeasurement).filter_by(astronaut_id=1).first()
    update_measurement(session,1,row.id,{'value':row.value+1},reason='Independent correction test')
    assert session.query(MeasurementRevision).filter_by(measurement_id=row.id).one().reason=='Independent correction test'
    with pytest.raises(ValueError):update_measurement(session,1,row.id,{'source':'REAL_SENSOR_DATA'})
    session.info['scenario']=False
    with pytest.raises(ValueError,match='active acquisition'):insert_measurement(session,1,dict(metric_name='heart_rate',value=72,unit='bpm',timestamp=datetime(2026,2,1),source='REAL_SENSOR_DATA'))


def test_correction_does_not_claim_edited_value_was_captured(session):
    import json
    session.info['scenario']=False
    batch=Batch('test-hrs','Fake backend, no physical validation',
        [dict(metric_name='heart_rate',value=72,unit='bpm',timestamp=datetime(2026,3,2))],
        'REAL_SENSOR_DATA','mock-capture',True)
    result=ingest(session,1,batch);record_id=result['measurement_ids'][0]
    proof=session.get(MeasurementProvenance,record_id)
    assert proof.capture_verified
    update_measurement(session,1,record_id,{'value':73},reason='Corrected test value')
    assert not proof.capture_verified
    assert json.loads(proof.details)['original_capture_verified']
    assert session.get(HealthMeasurement,record_id).source=='REAL_SENSOR_DATA'
    revision=session.query(MeasurementRevision).filter_by(measurement_id=record_id).one()
    assert json.loads(revision.before_json)['value']==72


def test_stable_folder_and_atomic_invalid_batch(session,tmp_path):
    folder=tmp_path/'incoming';folder.mkdir();path=folder/'measurements.csv'
    path.write_text('metric_name,value,unit,timestamp\nheart_rate,70,bpm,2026-02-01T00:00:00\n')
    connector=FolderConnector(folder)
    assert connector.poll()==[]
    batches=connector.poll();assert len(batches)==1
    connector.acknowledge(batches[0]);assert connector.poll()==[]
    with pytest.raises(ValueError,match='synthetic'):ingest(session,1,batches[0])
    before=session.query(HealthMeasurement).count()
    bad=Batch('synthetic-test','fixture',[{'metric_name':'heart_rate','value':70,'unit':'bpm','timestamp':datetime(2026,2,2)},
        {'metric_name':'heart_rate','value':999,'unit':'bpm','timestamp':datetime(2026,2,3)}],'SIMULATED_DATA','bad')
    with pytest.raises(ValueError):ingest(session,1,bad)
    assert session.query(HealthMeasurement).count()==before
    path.write_text('unfinished');assert connector.poll()==[];assert connector.poll()==[]


def test_ble_flags_rr_and_disconnect(session):
    assert parse_heart_rate(bytes([16,72,0,4]))['rr_ms']==[1000]
    assert parse_heart_rate(bytes([1,44,1]))['heart_rate']==300
    assert parse_heart_rate(bytes([4,72]))['quality']=='REVIEW'
    with pytest.raises(ValueError):parse_heart_rate(bytes([16,72,0]))
    class Fake:
        is_connected=True
        def __init__(self,*args):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):self.is_connected=False
        async def start_notify(self,uuid,callback):callback(None,bytes([0,72]))
        async def stop_notify(self,uuid):pass
    sensor=BluetoothSensor('TEST',simulated=True)
    batches=asyncio.run(sensor.collect(.01,Fake))
    assert sensor.state=='DISCONNECTED' and batches[0].source=='SIMULATED_DATA'
    assert ingest(session,1,batches[0])['capture_verified'] is False


def test_cleanup_does_not_delete_database_or_unknown_files(session):
    from services.retention import cleanup_scenario_artifacts
    root=Path(session.info['scenario_dir']);directory=root/'reports'/'test';directory.mkdir(parents=True)
    (directory/'theia_report.pdf').write_bytes(b'test');(directory/'user-notes.txt').write_text('keep')
    assert cleanup_scenario_artifacts(session,0)==['reports/test/theia_report.pdf'] or not (directory/'theia_report.pdf').exists()
    assert (root/'scenario.sqlite3').exists() and (directory/'user-notes.txt').exists()


def test_reserved_visual_port_never_selected_for_ohif(tmp_path,monkeypatch):
    import scripts.start_theia_services as launcher
    from services.ohif_runtime import ViewerStatus
    build=tmp_path/'build';build.mkdir()
    for name in ['index.html','app.js']:(build/name).write_text('fixture')
    spawned=[]
    class Process:
        def __init__(self,args,**kwargs):spawned.append(int(args[args.index('--port')+1]))
        def poll(self):return None
    monkeypatch.delenv('THEIA_OHIF_URL',raising=False)
    monkeypatch.setattr(launcher,'discovered_url',lambda *a:None)
    monkeypatch.setattr(launcher,'remember_service',lambda *a:None)
    monkeypatch.setattr(launcher,'is_port_open',lambda p:p in {3001,3003})
    monkeypatch.setattr(launcher,'probe_ohif',lambda url:ViewerStatus(url,bool(spawned and url.endswith(':'+str(spawned[-1]))),'fixture'))
    monkeypatch.setattr(launcher.subprocess,'Popen',Process)
    status,_=launcher.ensure_ohif(build)
    assert spawned==[3005] and status.ready


def test_additive_migration_preserves_legacy_rows_and_is_idempotent(tmp_path,monkeypatch):
    from sqlalchemy import create_engine,text
    from database.database import Base
    import database.database as database
    path=tmp_path/'legacy.sqlite3';engine=create_engine('sqlite:///'+str(path))
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        c.execute(text('DROP TABLE health_measurements'))
        c.execute(text('CREATE TABLE health_measurements (id INTEGER PRIMARY KEY, astronaut_id INTEGER, metric_name VARCHAR(100), value FLOAT, unit VARCHAR(50), timestamp DATETIME, source VARCHAR(100), data_quality_status VARCHAR(50), mission_context TEXT, notes TEXT)'))
        c.execute(text("INSERT INTO health_measurements VALUES (1,1,'heart_rate',73,'bpm','2026-01-01','MANUALLY_ENTERED_DATA','VALID',NULL,NULL)"))
    monkeypatch.setattr(database,'engine',engine);monkeypatch.setattr(database,'DB_PATH',path)
    database.init_db();database.init_db()
    with engine.connect() as c:
        assert c.execute(text('SELECT value FROM health_measurements')).scalar()==73
        assert c.execute(text('SELECT count(*) FROM schema_migrations')).scalar()==1
    assert list((tmp_path/'data/backups').glob('*.sqlite3'))
    engine.dispose()
