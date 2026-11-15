"""Guided, fully synthetic demonstration using the same production data services."""
import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut
from intelligence.engine import analyze
from services.scenario import add_scenario_measurement, reset_scenario
from services.analysis_views import render_analysis
from modules.ui.theme import render_page_header, info_card, navigation_button


def _reset():
    from services.scenario import scenario_factory
    with scenario_factory(st.session_state['scenario_workspace_id'])() as session:reset_scenario(session)
    for key in list(st.session_state):
        if key.startswith(('report_','history_','scenario_result','scenario_pdf')):
            st.session_state.pop(key,None)
    st.session_state['scenario_notice']='Scenario reset to the deterministic 30-day dataset.'


def render_scenario():
    render_page_header('Mission Scenario Mode','Reproducible scientific walkthrough / synthetic observations only')
    if not st.session_state.get('scenario_mode'):
        st.info('Enable Synthetic scenario workspace in the sidebar to enter an isolated SQLite workspace. Your normal mission storage remains separate.')
        return
    st.caption('REFERENCE DATASET / Two fictional profiles / Fixed January 2026 period / No real crew data')
    if st.session_state.get('scenario_notice'):st.success(st.session_state.pop('scenario_notice'))
    with SessionLocal() as session:
        astronaut=ensure_astronaut(session)
        result=analyze(session,astronaut.id)
        if st.session_state.get('scenario_pdf_snapshot') != result['fingerprint']:
            st.session_state.pop('scenario_pdf_bytes',None)
        columns=st.columns(3)
        with columns[0]:info_card('DEMO PROFILE',astronaut.name,'Choose either synthetic profile in the sidebar')
        with columns[1]:info_card('SYNTHETIC OBSERVATIONS',result['quality']['total'],'Deterministic 30-day reference series','violet')
        with columns[2]:info_card('STATISTICAL FLAGS',sum(len(x['anomalies']) for x in result['metrics'].values()),'Experimental statistical patterns only','amber')
        st.subheader('1 / Introduce a synthetic observation')
        st.caption('The default fatigue value is deliberately atypical relative to this generated series. This demonstrates statistics, not a clinical condition.')
        metric=st.selectbox('Scenario signal',['fatigue','sleep_hours','heart_rate'],key='scenario_signal')
        defaults={'fatigue':80.0,'sleep_hours':3.0,'heart_rate':110.0}
        from utils.measurement_schema import UNIT_BY_METRIC, METRIC_RANGES
        unit=next(iter(UNIT_BY_METRIC[metric]))
        value=st.number_input(f'Synthetic value ({unit})',min_value=float(METRIC_RANGES[metric][0]),max_value=float(METRIC_RANGES[metric][1]),value=defaults[metric],key=f'scenario_value_{metric}',help='Validated using the same metric ranges and units as other entries.')
        if st.button('Register synthetic measurement',key='scenario_add',icon=':material/add:'):
            try:
                record=add_scenario_measurement(session,astronaut.id,metric,value)
                st.session_state.pop('scenario_pdf_bytes',None)
                st.session_state['scenario_result']=f'Synthetic measurement {record.id} saved: {record.value:g} {record.unit} on {record.timestamp} UTC.'
                st.rerun()
            except ValueError as exc:st.error(str(exc))
        if st.session_state.get('scenario_result'):st.success(st.session_state['scenario_result'])
        st.subheader('2 / Inspect the same analysis across workspaces')
        with st.spinner('Computing the shared statistical snapshot…'):
            result=analyze(session,astronaut.id)
            render_analysis(session,astronaut.id,metric,'scenario')
        st.caption(f"Analysis snapshot: {result['fingerprint']}")
        cols=st.columns(3)
        with cols[0]:navigation_button('View Dashboard','Mission Overview','scenario_dashboard',':material/monitoring:')
        with cols[1]:navigation_button('Explain statistical flags','THEIA Intelligence Center','scenario_intelligence',':material/science:')
        with cols[2]:navigation_button('Explore digital anatomy','Human Body Explorer','scenario_anatomy',':material/accessibility_new:')
        st.subheader('3 / Generate a consistent PDF')
        if st.button('Generate scenario PDF',key='scenario_pdf_generate',icon=':material/picture_as_pdf:'):
            from modules.reports.reports import generate_pdf_report
            with st.spinner('Generating the synthetic scenario report…'):
                path=generate_pdf_report(session)
            st.session_state['scenario_pdf_bytes']=path.read_bytes()
            st.session_state['scenario_pdf_profile']=astronaut.id
            st.session_state['scenario_pdf_snapshot']=result['fingerprint']
            st.success('Synthetic PDF generated from the same snapshot.')
        if st.session_state.get('scenario_pdf_profile')==astronaut.id and 'scenario_pdf_bytes' in st.session_state:
            st.download_button('Download synthetic scenario PDF',st.session_state['scenario_pdf_bytes'],'theia-synthetic-scenario.pdf','application/pdf',key='scenario_pdf_download')
    st.divider()
    st.button('Reset synthetic scenario',key='scenario_reset',on_click=_reset,icon=':material/restart_alt:',help='Resets only this isolated session’s synthetic database, including synthetic derived analyses and report records.')
    st.caption('Switch off Synthetic scenario workspace to return to your original database. The two workspaces never share a database connection.')
