"""Readable explanations backed by the persisted statistical snapshot."""
import streamlit as st
from database.measurements import measurement_frame


def render_historical(session,astronaut_id,metric=None):
    from intelligence.historical import historical_analysis
    st.subheader('Independent historical reference')
    start=None
    custom=st.toggle('Evaluate a chosen historical window',key=f'historical_custom_{astronaut_id}_{metric}',help='Freeze the reference strictly before the selected UTC date instead of evaluating only each signal latest observation.')
    if custom:
        records=measurement_frame(session,astronaut_id,metric)
        if not records.empty:
            from datetime import datetime,time
            date=st.date_input('Evaluated window starts (UTC)',value=records.timestamp.max().date(),key=f'historical_start_{astronaut_id}_{metric}')
            start=datetime.combine(date,time.min)
    result=historical_analysis(session,astronaut_id,start=start)
    st.caption('Each signal/source evaluates its latest observation(s) against strictly earlier records. At least five samples on five observed days are required. No evaluated value enters its reference.')
    records=[item for item in result['signals'] if metric is None or item['metric']==metric]
    if not records:st.info('No compatible records for an independent reference.');return result
    for item in records:
        with st.expander(f"{item['metric']} / {item['source']} / {item['status']}",expanded=True):
            st.write(f"Reference before {item['reference_before']} UTC; {item['samples']} samples on {item['days']}/{item['span_days']} days.")
            st.write({'mean':item['mean'],'median':item['median'],'IQR':item['iqr'],'SD':item['std'],'unit':item['unit']})
            st.dataframe(item['observations'],hide_index=True)
            st.caption(item['method']);st.caption(result['limitations'])
            st.caption('Input reference IDs: '+', '.join(map(str,item['reference_ids'])))
    st.caption('Historical snapshot: '+result['fingerprint'])
    return result


def render_explanations(session, astronaut_id, result, metric=None):
    st.subheader('Explainable statistical review')
    st.caption('Inspect the observation, reference distribution and exact input records. No diagnostic interpretation is inferred.')
    records=[(item,flag) for item in result['metrics'].values() if metric is None or item['metric']==metric for flag in item['anomalies']]
    if not records:
        st.info('No statistical flags for the selected signal and cohort. This does not establish clinical normality; inspect sample sufficiency and source quality.')
        return
    def label(index):
        item,flag=records[index]
        return f"{item['metric']} / {flag['value']:g} {item['unit']} / {flag['timestamp']} / {item['cohort']}"
    latest=max(range(len(records)),key=lambda index:records[index][1]['timestamp'])
    index=st.selectbox('Statistical observation to explain',list(range(len(records))),index=latest,format_func=label,key=f"explanation_{astronaut_id}_{metric}_{result['fingerprint'][:12]}",help='Every flagged observation is available here; the latest is selected initially.')
    item,flag=records[index]
    with st.expander(label(index),expanded=True):
        cols=st.columns(3)
        cols[0].metric('Observed',f"{flag['value']:g} {item['unit']}")
        cols[1].metric('Reference mean',f"{flag['baseline_mean']:.3f} {item['unit']}")
        cols[2].metric('Deviation',f"{flag['deviation']:+.3f} {item['unit']}")
        st.write(flag['explanation'])
        st.caption(f"Method: {', '.join(flag['methods'])} · |z| = {flag['z_score']:.3f} · Reference SD = {flag['baseline_std']:.3f} · n = {flag['samples']}")
        if flag['isolation_decision_score'] is not None:
            st.caption(f"Isolation Forest decision score: {flag['isolation_decision_score']:.4f}; negative values are flagged. random_state=42; contamination=auto.")
        st.caption(f"Observation quality: {flag['quality']} · Source: {flag['source']} · Excluded records in selected analysis: {result['quality']['excluded']}")
        st.caption('VALID denotes schema, range and unit checks; it does not establish clinical verification or device calibration.')
        st.caption(flag['limitations'])
        frame=measurement_frame(session,astronaut_id)
        st.dataframe(frame[frame.id.isin(item['measurement_ids'])][['id','timestamp','value','unit','source','data_quality_status']],hide_index=True,height=240)
        st.caption(f"Snapshot {result['fingerprint']} · Parameters: {result['parameters']}")
