"""Native scientific tools, connected to the active profile and isolated scenario routing."""
import json
import pandas as pd
import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut
from database.measurements import measurement_frame
from services.scientific_health import longitudinal_analysis
from modules.ui.theme import render_page_header


def render_scientific_health():
    render_page_header('Scientific health analysis','Cardiovascular observations / sleep duration / mission periods / traceable methods')
    st.caption('Scalar observations support longitudinal descriptions. ECG, EEG and polysomnography are not present in the mission measurement schema.')
    tool=st.selectbox('Scientific tool',['Longitudinal periods','Beat-to-beat HRV','Open mHealth export'],key='science_tool')
    with SessionLocal() as session:
        astronaut=ensure_astronaut(session)
        if tool=='Beat-to-beat HRV':
            _render_hrv(session,astronaut.id)
            return
        frame=measurement_frame(session,astronaut.id)
        if frame.empty:
            st.info('No observations for this profile. Enter measurements or enable the synthetic scenario workspace.')
            return
        if tool=='Open mHealth export':
            from integrations.openmhealth import export_measurements
            st.caption('Pinned Open mHealth bodies: heart-rate 2.0, temperature 3.0, oxygen-saturation 2.0. Validated locally without network references. Provenance stays in a THEIA wrapper.')
            bundle=export_measurements(frame)
            st.metric('Validated bodies',len(bundle['points']))
            st.caption(f"{len(bundle['skipped'])} records have no verified mapping or fail quality checks. Sleep timestamps do not describe a sleep session interval; scalar pressure is not a systolic/diastolic pair.")
            st.download_button('Download validated Open mHealth bodies',json.dumps(bundle,indent=2),'theia-omh-bodies.json','application/json',key='science_omh_download')
            if bundle['points']:st.json(bundle['points'][0])
            if bundle['skipped']:st.dataframe(bundle['skipped'],hide_index=True)
            return
        first,last=frame.timestamp.min().date(),frame.timestamp.max().date()
        middle=first+(last-first)//2
        st.caption('Periods are user-selected UTC date ranges, not automatically inferred mission phases. At least five observed days in each period are needed for a comparison.')
        a=st.date_input('Reference period A',value=(first,middle),key=f'science_period_a_{astronaut.id}',help='Inclusive dates; choose a period distinct from B.')
        bstart=min(middle+pd.Timedelta(days=1),last)
        b=st.date_input('Comparison period B',value=(bstart,last),key=f'science_period_b_{astronaut.id}')
        try:
            with st.spinner('Preparing source-separated daily statistics…'):
                result=longitudinal_analysis(session,astronaut.id,(a,b))
        except ValueError as exc:
            st.info(str(exc));return
        signals=result['signals']
        if not signals:
            st.info('No observations pass the shared engine validation. Review units, timestamps and quality labels.');return
        index=st.selectbox('Scientific signal',range(len(signals)),format_func=lambda i:f"{signals[i]['metric']} / {signals[i]['source']}",key='science_signal')
        item=signals[index]
        cols=st.columns(3)
        cols[0].metric('Median daily value',f"{item['median']:.3f} {item['unit']}")
        cols[1].metric('Observed days',f"{item['days']} / {item['span_days']}")
        slope=item['theil_sen_per_day']
        cols[2].metric('Theil–Sen slope / day',f'{slope:+.4f}' if slope is not None else 'Insufficient days')
        chart=pd.DataFrame(item['daily']);chart['day']=pd.to_datetime(chart.day)
        st.line_chart(chart,x='day',y='value',x_label='UTC day',y_label=item['unit'],alt=f"Daily reported {item['metric']}, source {item['source']}")
        comparison=item['comparison']
        st.subheader('Period comparison')
        st.dataframe([{'period':label,**comparison[k]} for label,k in [('A','a'),('B','b')]],hide_index=True)
        if comparison['median_change'] is None:
            st.info('Insufficient days for comparison. Missing dates are not imputed.')
        else:
            st.write(f"B − A median change: {comparison['median_change']:+.3f} {item['unit']}.")
            st.caption('Descriptive difference only. Activity, acquisition method and mission conditions can differ; no causal or clinical inference.')
        if item['metric']=='sleep_hours':
            st.info('Sleep analysis describes reported duration and variability. It cannot determine REM/NREM, awakenings, sleep efficiency or a validated recovery score.')
        st.caption(f"IQR: {item['iqr']:.3f} {item['unit']} · Trend uses {item['trend_days_used']} observed daily means · Missing days preserved.")
        st.caption(result['limitations'])
        st.caption(f"Shared engine snapshot: {result['engine_snapshot']}")
        st.download_button('Download scientific analysis',json.dumps(result,indent=2),'theia-scientific-analysis.json','application/json',key='science_analysis_download')
        with st.expander('Input record identifiers and quality'):
            st.json({'measurement_ids':item['measurement_ids'],'quality':result['quality'],'fingerprint':result['fingerprint'],'method':result['method']})


def _render_hrv(session,astronaut_id):
    from integrations.cardiovascular import synthetic_nn,read_nn_csv,analyze_nn,save_nn_analysis
    st.info('Daily heart-rate measurements cannot yield HRV. This tool requires contiguous, reviewed normal-to-normal intervals in milliseconds.')
    demo=st.toggle('Use synthetic NN demonstration',value=True,key='science_nn_demo')
    data=None
    if demo:
        data=synthetic_nn();st.warning('SIMULATED_DATA · Deterministic artificial NN sequence, not astronaut physiology.')
    elif session.info.get('scenario'):
        st.info('External signal import is disabled in the exclusively synthetic workspace.');return
    else:
        uploaded=st.file_uploader('Reviewed NN intervals CSV (nn_ms)',type=['csv'],key='science_nn_upload')
        if uploaded:
            try:data=read_nn_csv(uploaded.getvalue())
            except (ValueError,UnicodeError) as exc:st.error(str(exc));return
    confirmed=st.checkbox('I confirm contiguous normal-to-normal intervals with no missing beats or untreated artifacts',key='science_nn_confirm')
    if st.button('Analyze NN intervals',key='science_nn_run',disabled=data is None or not confirmed):
        try:
            with st.spinner('Computing the verified NeuroKit-derived temporal subset…'):
                result=analyze_nn(data,'SIMULATED_DATA' if demo else 'IMPORTED_DATA',confirmed)
                row=save_nn_analysis(session,astronaut_id,result)
            st.session_state['science_nn_result']=(astronaut_id,bool(session.info.get('scenario')),row.id,result)
        except ValueError as exc:st.error(str(exc))
    stored=st.session_state.get('science_nn_result')
    if stored and stored[:2]==(astronaut_id,bool(session.info.get('scenario'))):
        result=stored[3]
        st.caption(f"Saved analysis {stored[2]} · {result['source']} · {result['library_version']} / reference {result['reference_version']} · {result['intervals']} NN intervals / {result['duration_seconds']:.1f} s")
        st.dataframe([{'statistic':k,'value':v,'unit':'%' if k=='HRV_pNN50' else 'ms'} for k,v in result['metrics'].items()],hide_index=True)
        st.line_chart(pd.DataFrame({'nn_ms':result['nn_ms']}),alt='Input normal-to-normal interval sequence in milliseconds')
        st.caption(result['quality']);st.caption('Four NumPy formulas adapted from NeuroKit2 (MIT); full NeuroKit is not executed. pNN50 uses N intervals as denominator, preserving the upstream convention.');st.caption(result['limitations'])
        st.download_button('Download traceable HRV result',json.dumps(result,indent=2),'theia-nn-hrv.json','application/json',key='science_nn_download')
