"""Readable explanations backed by the persisted statistical snapshot."""
import streamlit as st
from database.measurements import measurement_frame


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
