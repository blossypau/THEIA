import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut
from intelligence.engine import analyze
from services.report_builder import generate_pdf_report,report_input_fingerprint


def render_reports():
    with SessionLocal() as session:
        profile_id = ensure_astronaut(session).id
        from database.measurements import measurement_frame
        from datetime import datetime,time,timedelta
        frame=measurement_frame(session,profile_id)
        scope=st.selectbox('Report period',['All records','Custom UTC dates'],key='report_period_mode')
        start=end=None
        if scope=='Custom UTC dates' and not frame.empty:
            period=st.date_input('Report UTC date range',value=(frame.timestamp.min().date(),frame.timestamp.max().date()),key=f'report_dates_{profile_id}')
            if len(period)!=2:st.info('Select both report dates.');return
            start=datetime.combine(period[0],time.min);end=datetime.combine(period[1],time.max)
        current_snapshot = report_input_fingerprint(session,profile_id,start,end)
    if st.session_state.get('report_profile_id') != profile_id or st.session_state.get('report_snapshot') != current_snapshot:
        st.session_state.pop('report_bytes', None)
    st.caption("Mission Reports workspace")
    st.caption("PDF uses the same versioned statistical snapshot as Dashboard, Intelligence Center and anatomy panels.")
    if st.button("Generate PDF report", key="generate_report"):
        path = generate_pdf_report(start=start,end=end)
        st.session_state['report_bytes'] = path.read_bytes()
        st.session_state['report_profile_id'] = profile_id
        st.session_state['report_snapshot'] = current_snapshot
        st.success("Report generated and registered locally.")
    if 'report_bytes' in st.session_state:
        st.download_button("Download report", st.session_state['report_bytes'], "theia_report.pdf", "application/pdf")
