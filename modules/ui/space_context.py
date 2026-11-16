"""Functional hazard exploration within the existing mission and scientific pages."""
from datetime import datetime,timezone,timedelta
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from services.space_context import (HAZARDS,GRAVITY,GRAVITY_SOURCES,ENV_UNITS,context_frame,context_rows,
    add_context,import_context_csv,hazard_inventory,radiation_summary,propagation_seconds,phase_comparison)
from modules.ui.theme import navigation_button


def open_hazard(name):
    st.session_state['mission_hazard']=name
    st.session_state['science_tool']='Mission context & hazards'
    st.session_state['navigation']='Scientific Analysis'


def hazard_panel(session,astronaut_id):
    from services.space_context import observation_readiness
    with st.expander('Integrated observation readiness (not a diagnosis)'):
        st.dataframe(observation_readiness(session,astronaut_id),hide_index=True)
    st.subheader('Five human spaceflight hazards / recorded context')
    inventory=hazard_inventory(session,astronaut_id)
    columns=st.columns(5)
    for col,(name,info) in zip(columns,inventory.items()):
        with col:
            with st.container(border=True):
                st.caption(name.upper())
                st.metric('Context records',info['context_records'])
                st.caption(', '.join(info['recorded_sources']) or 'NO CONTEXT DATA')
                st.button('Explore evidence and data',key='hazard_'+name,on_click=open_hazard,args=(name,),width='stretch')
    gravity=context_rows(session,astronaut_id,'gravity')
    communications=context_rows(session,astronaut_id,'communications')
    if gravity:
        row=gravity[-1];p=json.loads(row.payload)
        st.caption(f"Latest recorded phase: {p['phase']} / {p['environment']} / {row.source} / {row.timestamp} UTC")
    if communications:
        row=communications[-1];p=json.loads(row.payload)
        delay=propagation_seconds(p['distance_km']) if p.get('distance_km') is not None else None
        st.caption(f"SIMULATED communications: {p['state']} / theoretical one-way propagation {delay:.3f} s" if delay is not None else f"SIMULATED communications: {p['state']} / distance unavailable")
    st.caption('NASA evidence is educational context, not telemetry, a medical risk score or proof that any hazard effect has been detected.')


def render_context(session,astronaut_id):
    selected=st.selectbox('Spaceflight hazard',list(HAZARDS),key='mission_hazard')
    definition=hazard_inventory(session,astronaut_id)[selected]
    st.write(definition['note']);st.link_button('Official NASA context',definition['url'])
    rows=context_rows(session,astronaut_id)
    relevant=[r for r in rows if r.kind in definition['kinds']]
    st.caption('Available physiological indicators: '+(', '.join(definition['available_metrics']) or 'NO COMPATIBLE PHYSIOLOGICAL DATA'))
    if not relevant:st.info('NO DATA for this hazard context. No exposure or environment is inferred from symptoms or anatomy.')
    frame=context_frame(session,astronaut_id)
    if relevant:
        st.dataframe([dict(id=r.id,kind=r.kind,timestamp=r.timestamp,end=r.end,source=r.source,quality=r.quality,instrument=r.instrument,**json.loads(r.payload)) for r in relevant],hide_index=True)
        if selected=='Space Radiation':
            summary=radiation_summary(relevant);st.dataframe(summary,hide_index=True)
            st.caption('Dose rates are integrated only over documented intervals. Overlaps refuse accumulation. Gy and Sv series remain separate; cumulative counters are never summed.')
        chart_rows=[]
        for r in relevant:
            p=json.loads(r.payload)
            if 'value' in p:chart_rows.append({'timestamp':r.timestamp,'value':p['value'],'series':str((p.get('metric',p.get('quantity')),p.get('unit','score'),p.get('origin',''),r.source,r.quality))})
        if chart_rows:
            chart=pd.DataFrame(chart_rows)
            series=st.selectbox('Context signal / unit / source',chart.series.unique(),key='hazard_context_series')
            plot=px.line(chart[chart.series==series],x='timestamp',y='value',markers=True,template='plotly_dark')
            st.plotly_chart(plot,width='stretch',key='context_chart',on_select='rerun')
        st.download_button('Download recorded hazard context',json.dumps([{'kind':r.kind,'timestamp':r.timestamp.isoformat(),'source':r.source,'quality':r.quality,'instrument':r.instrument,'payload':json.loads(r.payload)} for r in relevant],indent=2),'theia-context.json','application/json')
    if selected=='Altered Gravity Fields':
        st.dataframe([{'environment':k,'reference_m_s2':v[0],'meaning':v[1]} for k,v in GRAVITY.items()],hide_index=True)
        for url in GRAVITY_SOURCES:st.link_button('Physical reference',url)
        comparison=phase_comparison(session,astronaut_id)
        if comparison:st.dataframe(comparison,hide_index=True)
        st.caption('Phase comparisons require VALID observations and a recorded start/end interval; point contexts without an end cannot define a comparison period. Sources remain explicit. No bone-density, balance or muscle-performance measurement is invented.')
    if selected=='Distance from Earth':
        distance=st.number_input('Assumed geometric signal path (km)',min_value=0.,value=384400.,key='comms_distance')
        st.metric('Ideal one-way propagation',f'{propagation_seconds(distance):.3f} s')
        st.metric('Ideal round-trip propagation',f'{2*propagation_seconds(distance):.3f} s')
        st.caption('Calculation: distance / 299792.458 km/s (exact SI light speed). The supplied path is an assumption, not an ephemeris or measured network latency.')
        if session.info.get('scenario'):
            from database.models import TestOutbox
            from services.test_sync import synchronize
            available=st.toggle('SIMULATED test link available',value=False,key='test_link')
            st.metric('SYNC PENDING / synthetic outbox',session.query(TestOutbox).filter_by(status='SYNC PENDING').count())
            if st.button('Synchronize to local test SQLite mirror',key='test_sync'):
                st.json(synchronize(session,available))
    if selected=='Hostile/Closed Environments':
        from services.space_context import environment_associations
        associations=environment_associations(session,astronaut_id)
        if associations:
            st.caption('EXPLORATORY ASSOCIATION / not causal or clinically validated')
            st.dataframe(associations,hide_index=True)
        else:st.info('No compatible variable environmental/physiological signals on five paired UTC days with the same source. No association is inferred.')
    if not session.info.get('scenario'):
        with st.expander('Register declared context (not verified sensor acquisition)'):
            kind=st.selectbox('Context category',['gravity','environment','radiation','communications'],key='context_kind')
            with st.form('context_entry'):
                timestamp=st.datetime_input('Context start (UTC)',value=datetime.now(timezone.utc).replace(tzinfo=None),key='context_time')
                end=st.datetime_input('Context end (UTC)',value=datetime.now(timezone.utc).replace(tzinfo=None),key='context_end')
                instrument=st.text_input('Instrument or declared source',value='Manual mission context',key='context_instrument')
                if kind=='gravity':
                    payload={'environment':st.selectbox('Gravity environment',list(GRAVITY)), 'phase':st.text_input('Mission phase',value='Routine'),'activity':st.text_input('Recorded physical activity')}
                elif kind=='environment':
                    metric=st.selectbox('Environmental metric',list(ENV_UNITS))
                    payload={'metric':metric,'value':st.number_input('Environmental value',value=0.),'unit':ENV_UNITS[metric]}
                    st.caption('Unit: '+ENV_UNITS[metric]+'. No spacecraft safety threshold is inferred.')
                elif kind=='radiation':
                    payload={'origin':st.selectbox('Radiation origin',['GCR','SPE','TRAPPED','UNKNOWN']),
                        'basis':st.selectbox('Dosimetric quantity',['absorbed','equivalent']),
                        'quantity':st.selectbox('Observation type',['dose_increment','dose_rate','cumulative_reading']),
                        'value':st.number_input('Dosimeter value',min_value=0.),'unit':st.selectbox('Radiation unit',['mGy','uGy','Gy','mSv','uSv','Sv','mGy/h','uGy/h','mSv/h','uSv/h'])}
                    uncertainty_known=st.checkbox('Measurement uncertainty supplied')
                    payload['uncertainty']=st.number_input('Uncertainty in the same unit',min_value=0.) if uncertainty_known else None
                else:
                    payload={'state':st.selectbox('SIMULATED communication state',['OFFLINE','DELAYED','SYNC PENDING','CONNECTED']),
                        'distance_km':st.number_input('Assumed distance km',min_value=0.),'simulated_link':True}
                if st.form_submit_button('Save context'):
                    try:
                        add_context(session,astronaut_id,dict(kind=kind,timestamp=timestamp,end=end if end>timestamp else None,
                            instrument=instrument,source='SIMULATED_DATA' if kind=='communications' else 'MANUALLY_ENTERED_DATA',payload=payload))
                        st.success('Recorded context saved with explicit provenance.');st.rerun()
                    except ValueError as exc:st.error(str(exc))
        with st.expander('Import compatible dosimetry/environment/gravity CSV'):
            kind=st.selectbox('CSV context type',['radiation','environment','gravity'],key='context_csv_kind')
            st.caption('Common columns: timestamp,end,instrument,quality. Radiation: origin,basis,quantity,value,unit,uncertainty. Environment: metric,value,unit,sampling_seconds. Gravity: environment,phase. Imported files never become verified sensor data.')
            uploaded=st.file_uploader('Context CSV',type=['csv'],key='context_csv')
            if uploaded and st.button('Validate and import context CSV',key='context_import'):
                try:
                    imported=import_context_csv(session,astronaut_id,uploaded.getvalue(),kind);st.success(f'{len(imported)} contextual observations validated.')
                except (ValueError,OSError) as exc:session.rollback();st.error(str(exc))
