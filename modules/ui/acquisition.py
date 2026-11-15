"""Acquisition controls are shared by the existing mission workspaces."""
import asyncio
import json
import time
import streamlit as st
from database.database import SessionLocal
from database.repository import active_astronaut_id
from database.models import AcquisitionReceipt
from integrations.acquisition import SyntheticConnector,FolderConnector,APIConnector,ingest,record_error


@st.fragment(run_every='2s')
def acquisition_tick():
    source=st.session_state.get('acquisition_connector')
    target=st.session_state.get('acquisition_target')
    if source is None or not st.session_state.get('acquisition_running'):
        if st.session_state.get('follow_local_records'):
            from database.models import HealthMeasurement,MeasurementRevision,SpaceObservation
            from sqlalchemy import func
            profile=st.session_state.get('active_astronaut')
            if st.session_state.get('scenario_mode'):
                from services.scenario import scenario_factory
                factory=scenario_factory(st.session_state['scenario_workspace_id'])
            else:
                from database.database import _main_factory
                factory=_main_factory
            with factory() as session:
                signature=(session.query(func.max(HealthMeasurement.id)).filter_by(astronaut_id=profile).scalar(),
                    session.query(func.max(MeasurementRevision.id)).filter_by(astronaut_id=profile).scalar(),
                    session.query(func.max(SpaceObservation.id)).filter_by(astronaut_id=profile).scalar())
            key=f"record_watch_{profile}_{st.session_state.get('scenario_mode')}"
            previous=st.session_state.get(key);st.session_state[key]=signature
            if previous is not None and previous!=signature:st.rerun(scope='app')
        return
    now=time.monotonic()
    if now-st.session_state.get('acquisition_last_tick',0)<2:return
    st.session_state['acquisition_last_tick']=now
    current=(st.session_state.get('active_astronaut'),bool(st.session_state.get('scenario_mode')))
    if current!=target:
        st.session_state['acquisition_running']=False;return
    # Fragment reruns have an independent context; bind the factory explicitly.
    if current[1]:
        from services.scenario import scenario_factory
        factory=scenario_factory(st.session_state['scenario_workspace_id'])
    else:
        from database.database import _main_factory
        factory=_main_factory
    if isinstance(source,SyntheticConnector):source.speed=st.session_state.get("replay_speed",1)
    inserted=0
    with factory() as session:
        try:
            for batch in source.poll():
                result=ingest(session,current[0],batch);inserted+=len(result['measurement_ids'])
                if hasattr(source,'acknowledge'):source.acknowledge(batch)
                if isinstance(source,SyntheticConnector):
                    from services.space_context import demo_context
                    day=(batch.records[0]['timestamp']-__import__('datetime').datetime(2026,1,31,8)).days
                    demo_context(session,current[0],day)
                    if day==0:
                        from integrations.cardiovascular import synthetic_nn,analyze_nn,save_nn_analysis
                        result=analyze_nn(synthetic_nn(),'SIMULATED_DATA',True)
                        result['recording_start']='2026-01-31T08:00:00'
                        save_nn_analysis(session,current[0],result)
            if isinstance(source,SyntheticConnector) and source.state!='RUNNING':st.session_state['acquisition_running']=False
            st.caption(f"{'SIMULATED replay' if current[1] else 'Authorized source polling'} / {getattr(source,'state','POLLING')} / latest poll {inserted} observations")
            if inserted:st.rerun(scope='app')
        except Exception as exc:
            record_error(session,current[0],type(source).__name__,exc)
            st.session_state['acquisition_running']=False
            st.error(f'Acquisition paused: {exc}. Existing measurements were preserved.')


def render_acquisition(session,astronaut_id):
    st.subheader('Automatic acquisition')
    st.caption('Runs while this browser workspace is open. No acquisition daemon or NASA live telemetry is implied.')
    if session.info.get('scenario'):
        replay=st.session_state.get('acquisition_connector')
        scenario=st.selectbox('Replay scenario',['Long mission','Workload example'],key='replay_scenario',
            disabled=isinstance(replay,SyntheticConnector) and replay.position>0)
        speed=st.slider('Replay days per tick',1,10,1,key='replay_speed')
        def command(action):
            source=st.session_state.get('acquisition_connector')
            if not isinstance(source,SyntheticConnector) or source.scenario!=scenario:
                source=SyntheticConnector(scenario);st.session_state['acquisition_connector']=source
            source.speed=speed;source.command(action)
            st.session_state['acquisition_target']=(astronaut_id,True)
            st.session_state['acquisition_running']=source.state=='RUNNING'
        with st.container(horizontal=True):
            for label,action in [('Start automatic scenario','start'),('Pause acquisition','pause'),('Resume acquisition','resume'),('Stop acquisition','stop')]:
                st.button(label,key='acq_'+action,on_click=command,args=(action,))
        st.warning('SIMULATED: physiology and hazard values are artificial software examples, not a physiological model of spaceflight effects.')
    else:
        choice=st.selectbox('Authorized source',['Local folder','HTTPS API','Bluetooth Heart Rate Service'],key='acq_choice')
        if choice in {'Local folder','HTTPS API'}:
            address=st.text_input('Authorized folder path' if choice=='Local folder' else 'Authorized HTTPS measurements URL',key='acq_address')
            token=st.text_input('API token environment variable name (optional)',key='acq_token') if choice=='HTTPS API' else None
            if st.button('Start authorized polling',key='acq_poll_start'):
                try:
                    source=FolderConnector(address) if choice=='Local folder' else APIConnector(address,token or None)
                    st.session_state['acquisition_connector']=source
                    st.session_state['acquisition_target']=(astronaut_id,False)
                    st.session_state['acquisition_running']=True;st.rerun()
                except (OSError,ValueError) as exc:st.error(str(exc))
            if st.button('Stop authorized polling',key='acq_poll_stop'):st.session_state['acquisition_running']=False
            st.caption('CSV: metric_name,value,unit,timestamp; stable across polls and newline-terminated. Files are not moved or deleted. API: JSON list of the same fields; source is IMPORTED_DATA, not verified sensor capture.')
        else:
            from integrations.bluetooth_sensor import BluetoothSensor
            st.caption('Only compatible Bluetooth SIG HRS devices. No physical device has been validated for this release. Raw RR values are not automatically treated as reviewed NN intervals.')
            if st.button('Discover compatible HRS devices',key='ble_scan'):
                try:
                    with st.spinner('Scanning local Bluetooth adapter...'):st.session_state['ble_devices']=asyncio.run(BluetoothSensor.discover())
                except Exception as exc:st.error(f'Bluetooth unavailable: {exc}')
            devices=st.session_state.get('ble_devices',[])
            if not devices:st.info('NO DEVICE DATA. Scan requires a supported local adapter and a compatible sensor.')
            else:
                selected=st.selectbox('Discovered device',devices,format_func=lambda d:d['name'],key='ble_device')
                if st.button('Collect 5 seconds from selected HRS device',key='ble_collect'):
                    sensor=BluetoothSensor(selected['address'])
                    status=st.empty()
                    try:
                        with st.spinner('Connecting and subscribing to HRS notifications...'):
                            batches=asyncio.run(sensor.collect(5,on_state=lambda value:status.info('HRS state: '+value)))
                            for batch in batches:ingest(session,astronaut_id,batch)
                            st.session_state['unreviewed_ble_rr']='rr_ms\n'+'\n'.join(map(str,sensor.rr_ms))
                        st.success(f'{len(batches)} notification batches stored. Session ended: DISCONNECTED.')
                        st.caption('Verified capture means received from this connected HRS session; it does not certify device accuracy or calibration.')
                    except Exception as exc:record_error(session,astronaut_id,'ble-hrs',exc);st.error(str(exc))
            if st.session_state.get('unreviewed_ble_rr'):
                st.download_button('Download unreviewed RR for external review',st.session_state['unreviewed_ble_rr'],'unreviewed-rr.csv','text/csv')
                st.caption('Raw HRS RR is not automatically normal-to-normal. Review artifacts and gaps before any compatible NN analysis; do not simply relabel without review.')
    with st.expander('Acquisition receipts and errors'):
        rows=session.query(AcquisitionReceipt).filter_by(astronaut_id=astronaut_id).order_by(AcquisitionReceipt.timestamp.desc()).limit(30).all()
        st.dataframe([{'timestamp':r.timestamp,'connector':r.connector,'status':r.status,'details':r.details} for r in rows],hide_index=True)
