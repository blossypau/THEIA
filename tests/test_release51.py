"""Release integrity regressions; no real database, sensor or remote link is used."""
import io
import json
from datetime import datetime,timedelta
from uuid import uuid4
import numpy as np
import pytest
import requests
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker
from database.database import Base
from database.models import AstronautProfile,HealthMeasurement,MeasurementOrigin,MeasurementProvenance
from database.measurements import insert_measurement,update_measurement,measurement_frame
from integrations.acquisition import APIConnector,Batch,ingest,FolderConnector
from integrations.csv_import import import_csv
from integrations.cardiovascular import analyze_nn,synthetic_nn,save_nn_analysis
from services.provenance import profile_provenance,CLASSES
from services.scenario import scenario_factory


@pytest.fixture
def normal():
    engine=create_engine('sqlite:///:memory:');Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        s.add_all([AstronautProfile(name='Fictional A',mission_id='TEST'),AstronautProfile(name='Fictional B',mission_id='TEST')]);s.commit();yield s
    engine.dispose()


def payload(**kwargs):return dict(metric_name='heart_rate',value=72,unit='bpm',timestamp=datetime(2026,1,1),source='MANUALLY_ENTERED_DATA',**kwargs)


def test_legacy_is_unknown_and_no_receipt_time_invented(normal):
    normal.add(HealthMeasurement(astronaut_id=1,**payload()));normal.commit()
    result=profile_provenance(normal,1)[0]
    assert result['provenance_class']=='UNKNOWN_UNVERIFIED' and result['received_at'] is None
    assert not profile_provenance(normal,2)


@pytest.mark.parametrize('source,classification',[
    ('MANUALLY_ENTERED_DATA','MANUALLY_ENTERED_DATA'),('MANUAL_INPUT','MANUALLY_ENTERED_DATA'),
    ('IMPORTED_DATA','UNKNOWN_UNVERIFIED'),('PUBLIC_RESEARCH_DATA','UNKNOWN_UNVERIFIED')])
def test_classification_never_authenticates_declared_source(normal,source,classification):
    item=payload();item['source']=source;insert_measurement(normal,1,item)
    record=profile_provenance(normal,1)[0]
    assert record['provenance_class']==classification and record['received_at']>=record['measured_at']
    assert record['batch_id'] and not json.loads(record['provenance_evidence'])['identity_authenticated']


def test_transport_capture_revision_preserves_evidence_but_loses_verification(normal):
    item=payload();item.pop('source')
    result=ingest(normal,1,Batch('ble-hrs','FAKE BACKEND',[item],'REAL_SENSOR_DATA','fake',True))
    before=profile_provenance(normal,1)[0]
    assert before['provenance_class']=='VERIFIED_DEVICE_CAPTURE'
    assert before['device_id']=='FAKE BACKEND' and not json.loads(before['provenance_evidence'])['hardware_validated']
    update_measurement(normal,1,result['measurement_ids'][0],{'value':75},reason='Review')
    after=profile_provenance(normal,1)[0]
    assert after['provenance_class']=='UNKNOWN_UNVERIFIED' and after['revisions'][0]['before']['value']==72
    assert json.loads(after['provenance_evidence'])['capture_verified_at_receipt']


@pytest.mark.parametrize('route',['upload','folder','api'])
def test_synthetic_rows_rejected_by_normal_import_routes(normal,tmp_path,route):
    data=b'metric_name,value,unit,timestamp,source\nheart_rate,73,bpm,2026-01-02,SIMULATED_DATA\n'
    if route=='upload':
        with pytest.raises(ValueError,match='Synthetic'):import_csv(normal,io.BytesIO(data),1)
    else:
        if route=='folder':
            (tmp_path/'data.csv').write_bytes(data);connector=FolderConnector(tmp_path);connector.poll();batch=connector.poll()[0]
        else:
            item=payload();item['source']='SIMULATED_DATA';batch=Batch('authorized-api','FAKE',[item],'IMPORTED_DATA','fake')
        with pytest.raises(ValueError,match='Synthetic'):ingest(normal,1,batch)
    assert normal.query(HealthMeasurement).count()==0


def test_csv_hash_receipt_restart_and_profile_isolation(normal):
    data=b'metric_name,value,unit,timestamp\nheart_rate,73,bpm,2026-01-02T01:00:00+01:00\n'
    a=import_csv(normal,io.BytesIO(data),1)[0];b=import_csv(normal,io.BytesIO(data),1)[0]
    assert a.id==b.id and a.timestamp==datetime(2026,1,2)
    proof=profile_provenance(normal,1)[0]
    assert proof['acquisition_method']=='uploaded-csv' and proof['batch_id']
    import_csv(normal,io.BytesIO(data),2)
    assert len(profile_provenance(normal,2))==1 and proof['astronaut_id']==1


@pytest.mark.parametrize('data',[
    b'metric_name,value,timestamp\nheart_rate,73,2026-01-02\n',
    b'metric_name,value,unit,timestamp\nheart_rate,73,Hz,2026-01-02\n',
    b'metric_name,value,unit,timestamp\nheart_rate,73,bpm,not-a-date\n',
    b'metric_name,value,unit,timestamp\nheart_rate,NaN,bpm,2026-01-02\n'])
def test_bad_csv_atomic(normal,data):
    with pytest.raises(ValueError):import_csv(normal,io.BytesIO(data),1)
    assert normal.query(HealthMeasurement).count()==0


def test_api_timeout_bounded_retry_and_secret_redaction(monkeypatch):
    calls=[]
    def get(*a,**kw):calls.append(kw);raise requests.Timeout('secret token hiddenquery')
    monkeypatch.setattr(requests,'get',get);monkeypatch.setenv('THEIA_TEST_API_TOKEN','secret')
    with pytest.raises(ValueError) as exc:APIConnector('https://example.org/?key=hiddenquery','THEIA_TEST_API_TOKEN').poll()
    assert len(calls)==2 and all(c['headers']=={'Authorization':'Bearer secret'} for c in calls)
    assert 'secret' not in str(exc.value) and 'hiddenquery' not in str(exc.value)


def test_ble_no_notifications_cannot_produce_verified_data():
    import asyncio
    from integrations.bluetooth_sensor import BluetoothSensor
    class EmptyClient:
        is_connected=True
        def __init__(self,*args):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):self.is_connected=False
        async def start_notify(self,*args):pass
        async def stop_notify(self,*args):pass
    sensor=BluetoothSensor('FAKE')
    assert asyncio.run(sensor.collect(.01,EmptyClient))==[] and sensor.state=='DISCONNECTED'
    assert sensor.get_metadata()['hardware_validated'] is False


def test_nasa_offline_reference_not_astronaut_data(normal,monkeypatch):
    from services.nasa_power import load_reference,fetch_power
    monkeypatch.setattr(requests,'get',lambda *a,**kw:(_ for _ in ()).throw(requests.ConnectionError('offline')))
    with pytest.raises(requests.ConnectionError):fetch_power(normal)
    frame,_=load_reference()
    assert len(frame)==21 and set(frame.provenance_class)=={'NASA_PUBLIC_RESEARCH_DATA'}
    assert normal.query(HealthMeasurement).count()==0


def test_gravity_point_is_not_a_defined_comparison_period(normal):
    from services.space_context import add_context,phase_comparison
    insert_measurement(normal,1,payload())
    add_context(normal,1,dict(kind='gravity',timestamp=datetime(2026,1,1),instrument='Declared context',payload={'environment':'Moon','phase':'Instant only'}))
    assert phase_comparison(normal,1)==[]


def test_nn_constants_and_recording_identity(normal,tmp_path):
    result=analyze_nn(np.full(200,800.),'IMPORTED_DATA',True)
    assert result['metrics']=={'HRV_MeanNN':800.,'HRV_SDNN':0.,'HRV_RMSSD':0.,'HRV_pNN50':0.}
    first=save_nn_analysis(normal,1,dict(result,recording_start='2026-01-01T08:00:00'))
    second=save_nn_analysis(normal,1,dict(result,recording_start='2026-01-02T08:00:00'))
    assert first.id!=second.id
    forged=dict(result,metrics=dict(result['metrics'],HRV_RMSSD=99))
    with pytest.raises(ValueError,match='match'):save_nn_analysis(normal,1,forged)
    with pytest.raises(ValueError,match='isolated'):save_nn_analysis(normal,1,analyze_nn(synthetic_nn(),'SIMULATED_DATA',True))


def test_empty_report_and_snapshot_metadata(normal,tmp_path):
    from services.report_builder import generate_pdf_report
    from pypdf import PdfReader
    path=generate_pdf_report(normal,tmp_path/'empty.pdf',astronaut_id=2)
    text=' '.join(' '.join(p.extract_text() for p in PdfReader(path).pages).split())
    assert '0 observations' in text and 'NO DATA' in text and 'HARDWARE NOT VALIDATED' in text
    assert 'Fictional A' not in text and 'Fictional B' in text


def test_correction_invalidates_analysis_and_pdf_fingerprint(normal):
    from intelligence.engine import analyze
    from services.report_builder import report_input_fingerprint
    row=insert_measurement(normal,1,payload());a=analyze(normal,1);fingerprint=report_input_fingerprint(normal,1)
    update_measurement(normal,1,row.id,{'value':77},reason='Correction')
    assert analyze(normal,1)['fingerprint']!=a['fingerprint'] and report_input_fingerprint(normal,1)!=fingerprint


def test_independent_baseline_small_constant_zero_delta_and_no_future_leak(normal):
    from intelligence.historical import historical_analysis
    for day in range(5):
        item=payload();item['timestamp']+=timedelta(days=day);insert_measurement(normal,1,item)
    latest=payload();latest.update(timestamp=datetime(2026,1,6),value=73);insert_measurement(normal,1,latest)
    result=historical_analysis(normal,1,start=datetime(2026,1,6))['signals'][0]
    assert result['std']==0 and result['observations'][0]['z_score'] is None and result['observations'][0]['flagged']
    assert result['samples']==5 and result['reference_ids']==[1,2,3,4,5]
    small=historical_analysis(normal,1,start=datetime(2026,1,3))['signals'][0]
    assert small['status']=='insufficient_history' and not any(o['flagged'] for o in small['observations'])


def test_longitudinal_closed_form_units_coverage_and_zero_percent_denominator(normal):
    from services.scientific_health import longitudinal_analysis
    for day in range(10):
        item=payload();item.update(timestamp=datetime(2026,1,1)+timedelta(days=day),value=60+2*day);insert_measurement(normal,1,item)
        item.update(metric_name='fatigue',unit='score',value=0 if day<5 else 10);insert_measurement(normal,1,item)
    result=longitudinal_analysis(normal,1,periods=[('2026-01-01','2026-01-05'),('2026-01-06','2026-01-10')])
    pulse=next(i for i in result['signals'] if i['metric']=='heart_rate')
    assert pulse['median']==69 and pulse['iqr']==9 and pulse['theil_sen_per_day']==2 and pulse['observed_day_fraction']==1
    assert pulse['comparison']['median_change']==10 and pulse['comparison']['percent_change']==pytest.approx(1000/64)
    fatigue=next(i for i in result['signals'] if i['metric']=='fatigue')
    assert fatigue['comparison']['median_change']==10 and fatigue['comparison']['percent_change'] is None


def test_ohif_failure_then_recovery_has_no_persisted_false_readiness(monkeypatch):
    from services.ohif_runtime import ViewerStatus
    import services.ui_status as status
    monkeypatch.setattr(status.requests,'get',lambda *a,**kw:(_ for _ in ()).throw(requests.ConnectionError('offline')))
    ready=[False]
    monkeypatch.setattr(status,'resolve_ohif',lambda:ViewerStatus('http://127.0.0.1:3003',ready[0],'test'))
    status.service_snapshot.clear();assert not status.service_snapshot()['OHIF']
    ready[0]=True;status.service_snapshot.clear();assert status.service_snapshot()['OHIF']


def test_normal_hrv_ui_has_no_synthetic_generator():
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=45).run()
    app.radio(key='navigation').set_value('Scientific Analysis').run()
    app.selectbox(key='science_tool').set_value('Beat-to-beat HRV').run()
    assert not app.exception
    assert not any(t.key=='science_nn_demo' for t in app.toggle)
    assert not any('SIMULATED_DATA' in t.value for t in app.warning)


def test_voluntary_social_consent_form_stores_entered_value():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from services.space_context import context_frame
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=45).run()
    app.toggle(key='scenario_mode').set_value(True).run()
    app.radio(key='navigation').set_value('Daily Check-in').run()
    assert app.number_input(key='checkin_social_minutes').value is None
    next(c for c in app.checkbox if c.label=='Voluntarily log social interaction minutes').check()
    app.number_input(key='checkin_social_minutes').set_value(42.)
    next(b for b in app.button if b.label=='Save check-in').click().run()
    assert not app.exception
    with scenario_factory(app.session_state['scenario_workspace_id'])() as s:
        rows=context_frame(s,app.session_state['active_astronaut'],'wellbeing')
        assert rows[rows.metric=='social_minutes'].value.tolist()==[42.]


def test_nutrition_distinguishes_unknown_and_explicit_zero():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from database.models import NutritionRecord
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=45).run()
    app.toggle(key='scenario_mode').set_value(True).run()
    app.radio(key='navigation').set_value('Nutrition').run()
    next(t for t in app.text_input if t.label=='Meal or food item').set_value('Fictional test meal')
    next(n for n in app.number_input if n.label=='Calories').set_value(0.)
    next(b for b in app.button if b.label=='Save nutrition record').click().run()
    assert not app.exception
    with scenario_factory(app.session_state['scenario_workspace_id'])() as s:
        item=s.query(NutritionRecord).filter_by(astronaut_id=app.session_state['active_astronaut']).one()
        assert item.calories==0 and item.hydration_liters is None
