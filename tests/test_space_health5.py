from datetime import datetime,timedelta
from uuid import uuid4
import asyncio
import json
from pathlib import Path
import numpy as np
import pytest
from pypdf import PdfReader
from sqlalchemy import text
from database.models import HealthMeasurement,SpaceObservation,TestOutbox,SchemaMigration
from services.scenario import scenario_factory,reset_scenario
from services.space_context import (add_context,demo_context,radiation_summary,context_rows,propagation_seconds,
    hazard_inventory,import_context_csv,environment_associations)
from integrations.acquisition import SyntheticConnector,ingest,APIConnector
from integrations.cardiovascular import analyze_nn,synthetic_nn,save_nn_analysis


@pytest.fixture
def session(tmp_path):
    with scenario_factory(str(uuid4()),str(tmp_path))() as s:yield s


def dose(session,value=2,unit='mGy/h',start=0,end=2,basis='absorbed',quantity='dose_rate'):
    return add_context(session,1,dict(kind='radiation',timestamp=datetime(2026,2,1)+timedelta(hours=start),
        end=datetime(2026,2,1)+timedelta(hours=end) if end is not None else None,source='SIMULATED_DATA',instrument='Synthetic dosimeter',
        payload=dict(origin='GCR',basis=basis,quantity=quantity,value=value,unit=unit,uncertainty=None)))


def test_dose_rate_integration_and_no_gy_sv_conversion(session):
    dose(session)
    summary=radiation_summary(context_rows(session,1,'radiation'))
    assert summary[0]['interval_sum']==pytest.approx(.004) and summary[0]['unit']=='Gy'
    with pytest.raises(ValueError):dose(session,unit='mSv/h',basis='absorbed')
    dose(session,unit='mSv/h',basis='equivalent')
    assert len(radiation_summary(context_rows(session,1,'radiation')))==2


def test_overlap_refused_and_cumulative_not_summed(session):
    dose(session);dose(session,start=1,end=3)
    assert radiation_summary(context_rows(session,1,'radiation'))[0]['interval_sum'] is None
    session.query(SpaceObservation).delete();session.commit()
    dose(session,value=2,unit='mGy',start=0,end=None,quantity='cumulative_reading')
    dose(session,value=5,unit='mGy',start=3,end=None,quantity='cumulative_reading')
    result=radiation_summary(context_rows(session,1,'radiation'))[0]
    assert result['interval_sum'] is None and result['cumulative_change']==pytest.approx(.003)


@pytest.mark.parametrize('payload',[
    {'kind':'environment','payload':{'metric':'co2','value':500,'unit':'C'}},
    {'kind':'environment','payload':{'metric':'humidity','value':101,'unit':'%'}},
    {'kind':'wellbeing','payload':{'metric':'social_minutes','value':10,'consent':False}},
    {'kind':'communications','payload':{'state':'CONNECTED','simulated_link':False}},
    {'kind':'gravity','payload':{'environment':'Unknown planet','phase':'X'}}])
def test_invalid_context_units_consent_and_claims(session,payload):
    with pytest.raises(ValueError):add_context(session,1,dict(timestamp=datetime(2026,2,1),instrument='fixture',source='SIMULATED_DATA',**payload))


def test_automatic_mission_hazards_sync_and_reset(session):
    replay=SyntheticConnector();replay.command('start');replay.speed=10
    for batch in replay.poll():
        ingest(session,1,batch)
        day=(batch.records[0]['timestamp']-datetime(2026,1,31,8)).days
        demo_context(session,1,day)
    inventory=hazard_inventory(session,1)
    assert len(inventory)==5 and all(item['context_records']>0 for item in inventory.values())
    assert session.query(TestOutbox).count()==10
    from services.test_sync import synchronize
    assert synchronize(session,False)['state']=='OFFLINE'
    assert synchronize(session,True)['sent']==10 and synchronize(session,True)['sent']==0
    assert session.query(TestOutbox).filter_by(status='SYNC PENDING').count()==0
    assert environment_associations(session,1)
    reset_scenario(session)
    assert session.query(SpaceObservation).count()==0 and session.query(TestOutbox).count()==0
    assert session.query(HealthMeasurement).count()==300


def test_propagation_is_physical_not_network_latency():
    assert propagation_seconds(299792.458)==1
    assert propagation_seconds(384400)==pytest.approx(1.28222038194)
    with pytest.raises(ValueError):propagation_seconds(-1)


def test_nn_units_artifacts_missing_and_continuity():
    values=synthetic_nn();times=np.cumsum(values)/1000
    result=analyze_nn(values,'SIMULATED_DATA',True,end_time_s=times,artifact_flags=np.zeros(len(values)))
    assert 'continuity checked' in result['quality']
    times[50:]+=1
    with pytest.raises(ValueError,match='Noncontiguous'):analyze_nn(values,'SIMULATED_DATA',True,end_time_s=times)
    with pytest.raises(ValueError):analyze_nn(values,'SIMULATED_DATA',True,artifact_flags=np.ones(len(values)))
    with pytest.raises(ValueError):analyze_nn(values,'SIMULATED_DATA',True,unit='seconds')


def test_nasa_power_real_quantitative_reference_and_units():
    from services.nasa_power import load_reference,parse_power
    frame,metadata=load_reference()
    assert len(frame)==21 and frame.source.unique().tolist()==['PUBLIC_RESEARCH_DATA']
    assert frame[(frame.metric=='temperature')].value.iloc[0]==16.35
    assert frame[(frame.metric=='pressure')].unit.unique().tolist()==['kPa']
    assert 'not cabin' in metadata['scope']


def test_api_polling_real_files_and_provenance_downgrade(session,monkeypatch):
    import requests
    payload=[dict(metric_name='heart_rate',value=74,unit='bpm',timestamp='2026-02-01T08:00:00',source='REAL_SENSOR_DATA')]
    class Response:
        status_code=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_content(self,*args):yield json.dumps(payload).encode()
    monkeypatch.setattr(requests,'get',lambda *a,**kw:Response())
    connector=APIConnector('https://example.org/authorized')
    batch=connector.poll()[0]
    assert batch.source=='IMPORTED_DATA' and not batch.capture_verified
    with pytest.raises(ValueError):ingest(session,1,batch)
    session.info['scenario']=False
    first=ingest(session,1,batch);second=ingest(session,1,batch)
    assert first==second and first['source']=='IMPORTED_DATA'


def test_ble_reconnect_and_bounded_disconnect():
    from integrations.bluetooth_sensor import BluetoothSensor
    attempts=[]
    class Client:
        is_connected=True
        def __init__(self,*args):attempts.append(1)
        async def __aenter__(self):
            if len(attempts)==1:raise ConnectionError('Synthetic disconnection')
            return self
        async def __aexit__(self,*args):pass
        async def start_notify(self,u,callback):callback(None,bytes([0,72]))
        async def stop_notify(self,u):pass
    sensor=BluetoothSensor('FAKE',simulated=True)
    assert asyncio.run(sensor.collect(.01,Client))
    assert len(attempts)==2 and sensor.state=='DISCONNECTED' and sensor.errors


def test_scientific_pdf_context_hrv_and_profile_scope(session,tmp_path):
    demo_context(session,1,0)
    result=analyze_nn(synthetic_nn(),'SIMULATED_DATA',True);save_nn_analysis(session,1,result)
    from services.report_builder import generate_pdf_report
    from database.repository import active_astronaut_id,get_report_documents
    token=active_astronaut_id.set(1)
    try:
        path=generate_pdf_report(session,tmp_path/'report.pdf')
        text='\n'.join(page.extract_text() for page in PdfReader(path).pages)
        assert 'HRV_RMSSD' in text and 'Recorded mission context' in text and 'Independent personal reference' in text
        assert get_report_documents(session)
    finally:active_astronaut_id.reset(token)
    token=active_astronaut_id.set(2)
    try:assert not get_report_documents(session)
    finally:active_astronaut_id.reset(token)


def test_report_cache_changes_with_context_and_nn(session):
    from services.report_builder import report_input_fingerprint
    before=report_input_fingerprint(session,1)
    demo_context(session,1,0)
    after_context=report_input_fingerprint(session,1)
    assert after_context!=before
    save_nn_analysis(session,1,analyze_nn(synthetic_nn(),'SIMULATED_DATA',True))
    assert report_input_fingerprint(session,1)!=after_context


def test_empty_data_ui_and_manual_sensor_option_removed():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=45).run()
    app.toggle(key='scenario_mode').set_value(True).run()
    app.radio(key='navigation').set_value('Data Management').run()
    app.date_input(key='data_period').set_value((datetime(2020,1,1).date(),datetime(2020,1,2).date())).run()
    assert not app.exception
    assert any('No measurements match' in item.value for item in app.info)
    app.radio(key='navigation').set_value('Scientific Analysis').run()
    app.selectbox(key='science_tool').set_value('Mission context & hazards').run()
    assert not app.exception and any('NO DATA' in item.value for item in app.info)
