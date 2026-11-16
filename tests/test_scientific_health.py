"""Scientific capabilities are tested with isolated, explicitly synthetic inputs."""
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.database import Base
from database.models import AstronautProfile, ScientificAnalysisRecord
from database.measurements import insert_measurement,measurement_frame,update_measurement
from intelligence.engine import analyze
from services.scientific_health import longitudinal_analysis
from integrations.cardiovascular import analyze_nn,synthetic_nn,read_nn_csv,save_nn_analysis
from integrations.openmhealth import export_measurements,validate_body,SCHEMAS


@pytest.fixture
def session():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        s.add(AstronautProfile(name='Synthetic science test',mission_id='SCIENCE-TEST'));s.commit()
        yield s
    engine.dispose()


def add(session,metric,value,day,source='SIMULATED_DATA',quality='VALID',hour=0):
    units={'heart_rate':'bpm','sleep_hours':'hours','body_temperature':'C','oxygen_saturation':'%','fatigue':'score'}
    return insert_measurement(session,1,dict(metric_name=metric,value=value,unit=units[metric],
        timestamp=datetime(2026,1,1)+timedelta(days=day,hours=hour),source=source,data_quality_status=quality))


def test_periods_trend_daily_weighting_and_exact_sources(session):
    for day in range(12):
        add(session,'heart_rate',60+day,day)
        add(session,'heart_rate',100,day,'MANUALLY_ENTERED_DATA',hour=2)
    # Duplicate sampling on a single day cannot give that day more trend weight.
    add(session,'heart_rate',60,0,hour=1)
    add(session,'heart_rate',180,13,quality='REVIEW')
    periods=(('2026-01-01','2026-01-06'),('2026-01-07','2026-01-12'))
    result=longitudinal_analysis(session,1,periods)
    assert result['quality']['excluded']==1
    assert len(result['signals'])==2
    sim=next(i for i in result['signals'] if i['source']=='SIMULATED_DATA')
    assert sim['days']==12 and sim['observations']==13
    assert sim['theil_sen_per_day']==pytest.approx(1)
    assert sim['comparison']['median_change']==pytest.approx(6)
    assert len(sim['measurement_ids'])==13
    assert longitudinal_analysis(session,1,periods)==result
    assert session.query(ScientificAnalysisRecord).filter_by(analysis_type='longitudinal_health').count()==1


@pytest.mark.parametrize('periods',[
    (('2026-01-01','2026-01-06'),('2026-01-06','2026-01-12')),
    (('2026-01-06','2026-01-01'),('2026-01-07','2026-01-12')),
    (('2026-01-01',),('2026-01-07','2026-01-12'))])
def test_invalid_periods_rejected(session,periods):
    with pytest.raises(ValueError):longitudinal_analysis(session,1,periods)


def test_empty_missing_days_and_insufficient_periods(session):
    assert longitudinal_analysis(session,1,persist=False)['signals']==[]
    add(session,'sleep_hours',7,0);add(session,'sleep_hours',6,9)
    result=longitudinal_analysis(session,1,(('2026-01-01','2026-01-05'),('2026-01-06','2026-01-10')),persist=False)
    item=result['signals'][0]
    assert item['observed_day_fraction']==pytest.approx(.2)
    assert item['theil_sen_per_day'] is None and item['comparison']['median_change'] is None
    assert len(item['daily'])==2 and 'not sleep staging' in result['limitations']


def test_microsecond_correction_invalidates_engine_and_scientific_results(session):
    row=add(session,'heart_rate',70,0)
    update_measurement(session,1,row.id,{'timestamp':datetime(2026,1,1,0,0,0,123100)})
    first=longitudinal_analysis(session,1)
    update_measurement(session,1,row.id,{'timestamp':datetime(2026,1,1,0,0,0,123200)})
    second=longitudinal_analysis(session,1)
    assert first['engine_snapshot']!=second['engine_snapshot']
    assert analyze(session,1)['metrics']['heart_rate:simulated']['latest_timestamp'].endswith('123200')


def test_nn_analytic_reference_values_and_upstream_denominator(session):
    values=np.tile([800.,900.],100)
    result=analyze_nn(values,'SIMULATED_DATA',True)
    assert result['metrics']['HRV_MeanNN']==850
    assert result['metrics']['HRV_SDNN']==pytest.approx(50*np.sqrt(200/199))
    assert result['metrics']['HRV_RMSSD']==100
    assert result['metrics']['HRV_pNN50']==99.5
    assert result['duration_seconds']==170
    session.info['scenario']=True  # Isolated in-memory synthetic NN workspace.
    first=save_nn_analysis(session,1,result);second=save_nn_analysis(session,1,result)
    assert first.id==second.id
    stored=json.loads(first.result_summary)
    assert stored['nn_ms']==values.tolist() and stored['source']=='SIMULATED_DATA'


@pytest.mark.parametrize('values,source,confirmed',[
    ([800]*119,'SIMULATED_DATA',True),([800]*120,'SIMULATED_DATA',True),
    ([800]*200,'REAL_SENSOR_DATA',True),([800]*200,'IMPORTED_DATA',False),
    ([float('nan')]*200,'IMPORTED_DATA',True),([4000]*200,'IMPORTED_DATA',True)])
def test_nn_invalid_short_unconfirmed_or_nonfinite_rejected(values,source,confirmed):
    with pytest.raises(ValueError):analyze_nn(values,source,confirmed)


def test_nn_csv_and_synthetic_isolation(tmp_path):
    with pytest.raises(ValueError):read_nn_csv(b'heart_rate\n70\n71\n')
    assert read_nn_csv(b'nn_ms\n800\n900\n').tolist()==[800,900]
    from services.scenario import scenario_factory
    with scenario_factory(str(uuid4()),str(tmp_path))() as s:
        result=analyze_nn(synthetic_nn(),'IMPORTED_DATA',True)
        with pytest.raises(ValueError,match='synthetic workspace'):save_nn_analysis(s,1,result)
        result=analyze_nn(synthetic_nn(),'SIMULATED_DATA',True)
        assert save_nn_analysis(s,1,result).id


def test_omh_offline_export_preserves_provenance_and_skips_unsupported(session,monkeypatch):
    import requests
    monkeypatch.setattr(requests,'get',lambda *a,**kw:pytest.fail('Schema validation must be offline'))
    add(session,'heart_rate',72,0);add(session,'sleep_hours',7,0)
    add(session,'body_temperature',36.7,0);add(session,'oxygen_saturation',98,0)
    add(session,'heart_rate',73,1,quality='REVIEW')
    result=export_measurements(measurement_frame(session,1))
    assert len(result['points'])==3 and len(result['skipped'])==2
    assert all(p['theia_provenance']['source']=='SIMULATED_DATA' for p in result['points'])
    assert result['points'][0]['body']['heart_rate']['unit']=='beats/min'
    manifest=json.loads((SCHEMAS/'manifest.json').read_text())
    for name,digest in manifest['files'].items():assert hashlib.sha256((SCHEMAS/name).read_bytes()).hexdigest()==digest


def test_omh_rejects_incorrect_units_and_dates():
    from jsonschema import ValidationError
    with pytest.raises(ValidationError):validate_body('heart_rate',{'heart_rate':{'value':72,'unit':'C'},'effective_time_frame':{'date_time':'2026-01-01T00:00:00Z'}})
    with pytest.raises(ValidationError):validate_body('heart_rate',{'heart_rate':{'value':72,'unit':'beats/min'},'effective_time_frame':{'date_time':'yesterday'}})


def test_public_dicom_download_and_integrity_rejection(monkeypatch):
    from services.public_dicom import fetch_sample,verify_sample,sample_manifest
    import requests
    with pytest.raises(ValueError,match='hash mismatch'):verify_sample(b'not DICOM')
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_content(self,*args):yield b'bad'
    urls=[]
    def get(url,**kwargs):urls.append(url);return Response()
    monkeypatch.setattr(requests,'get',get)
    with pytest.raises(ValueError):fetch_sample()
    assert sample_manifest()['revision'] in urls[0] and urls[0].startswith('https://raw.githubusercontent.com/OHIF/viewer-testdata/')


def test_scientific_ui_periods_export_hrv_and_reset():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=45).run()
    app.toggle(key='scenario_mode').set_value(True).run()
    app.radio(key='navigation').set_value('Scientific Analysis').run()
    assert not app.exception
    assert any('B − A median change' in v.value for v in app.markdown)
    app.selectbox(key='science_tool').set_value('Open mHealth export').run()
    assert not app.exception and app.metric[0].value=='90'
    app.selectbox(key='science_tool').set_value('Beat-to-beat HRV').run()
    app.checkbox(key='science_nn_confirm').check().run()
    app.button(key='science_nn_run').click().run()
    assert not app.exception and app.session_state['science_nn_result'][3]['source']=='SIMULATED_DATA'
    app.radio(key='navigation').set_value('Mission Scenario Mode').run()
    app.button(key='scenario_reset').click().run()
    assert not app.exception and 'science_nn_result' not in app.session_state


def test_concurrent_synthetic_initialization_and_foreign_keys(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from services.scenario import scenario_factory
    identifier=str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        factories=list(pool.map(lambda _:scenario_factory(identifier,str(tmp_path)),range(4)))
    for factory in factories:
        with factory() as s:
            assert s.query(AstronautProfile).count()==2
            assert s.execute(text('SELECT count(*) FROM health_measurements')).scalar()==300
            assert s.execute(text('PRAGMA foreign_keys')).scalar()==1
    with factories[0]() as s:
        with pytest.raises(IntegrityError):
            s.execute(text("INSERT INTO mission_events (astronaut_id,event_type,description,mission_day,timestamp) VALUES (999,'test','synthetic',1,'2026-01-01')"))
        s.rollback()
