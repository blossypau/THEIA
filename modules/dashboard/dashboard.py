from datetime import datetime, timezone, timedelta
from html import escape
import pandas as pd
import streamlit as st
from database.database import SessionLocal
from database.models import AstronautProfile
from database.repository import ensure_astronaut, get_dashboard_summary, get_mission_events
from database.measurements import measurement_frame
from intelligence.engine import analyze
from services.analysis_views import render_analysis, metric_view, history_figure
from modules.ui.theme import apply_theia_theme, render_page_header, section_heading, info_card, navigation_button
from services.ui_status import service_snapshot, VISUAL_URL
from utils.measurement_schema import ALLOWED_METRICS


def _services():
    states=service_snapshot()
    html=''.join(f"<span class='service-chip {'ready' if ready else 'offline'}'>{escape(name)} / {'HTTP VERIFIED' if ready else 'UNAVAILABLE'}</span>" for name,ready in states.items())
    st.markdown(f"<div class='service-strip'>{html}<span class='service-chip'>SQLite / LOCAL STORAGE</span></div>",unsafe_allow_html=True)
    return states


def _signal(session,astronaut_id,metric,label):
    frame=measurement_frame(session,astronaut_id,metric)
    with st.container(border=True):
        if frame.empty:
            st.metric(label,'—',help='No recorded observations for this astronaut.')
            st.caption('NO DATA / awaiting measurement')
        else:
            latest=frame.iloc[-1]
            st.metric(label,f'{latest.value:g} {latest.unit}',chart_data=frame.value.tail(20).tolist(),chart_type='line')
            from database.models import MeasurementProvenance
            proof=session.get(MeasurementProvenance,int(latest.id))
            st.caption('Recorded HRS capture; calibration not verified' if proof is not None and proof.capture_verified else 'Declared/imported/synthetic source; no physical capture verified')
            st.caption(f"{latest.source} · {latest.timestamp:%d %b %H:%M} UTC")


def render_dashboard():
    apply_theia_theme()
    render_page_header('Mission Control','A continuous view of the person behind the mission.')
    states=_services()
    with SessionLocal() as session:
        summary=get_dashboard_summary(session);astronaut=summary['astronaut'];result=summary['analysis']
        from intelligence.historical import historical_analysis
        independent=historical_analysis(session,astronaut.id)
        with st.container(key='mission_stage'):
            signals,scene,readouts=st.columns([1,2.5,1],gap='medium')
            with signals:
                section_heading('Vital signals','LATEST RECORDED')
                for metric,label in [('heart_rate','Heart rate'),('oxygen_saturation','Oxygen saturation'),('body_temperature','Temperature')]:_signal(session,astronaut.id,metric,label)
            with scene:
                if states['Anatomy / 3D']:
                    st.iframe(VISUAL_URL+'/orbit.html',height=470,alt='Interactive illustrative orbital station. Drag to rotate and scroll to zoom.')
                else:
                    info_card('3D WORKSPACE','Scene offline','Start scripts/start_theia_services.py to enable the local orbital scene.')
                left,right=st.columns(2)
                with left:navigation_button('Explore human anatomy','Human Body Explorer','overview_anatomy',':material/accessibility_new:')
                with right:navigation_button('Open health analytics','Health Dashboard','overview_health',':material/monitoring:')
            with readouts:
                section_heading('Data readiness','VERIFIABLE')
                info_card('OBSERVATIONS',result['quality']['total'],'Measurements stored for the active astronaut')
                info_card('STATISTICAL FLAGS',sum(o['flagged'] for v in independent['signals'] for o in v['observations']),'Prior-history deviations / not diagnoses','violet')
                info_card('EXCLUDED RECORDS',result['quality']['excluded'],'Quality / range / unit validation','amber')
                info_card('MISSION DAY',f'{astronaut.mission_day:03}',astronaut.mission_id,'green')
        from modules.ui.space_context import hazard_panel
        hazard_panel(session,astronaut.id)
        section_heading('Crew health workspace','REGISTERED PROFILES ONLY')
        profiles=session.query(AstronautProfile).order_by(AstronautProfile.id).all()
        columns=st.columns(min(4,max(1,len(profiles))))
        for index,profile in enumerate(profiles):
            with columns[index%len(columns)]:
                initials=''.join(word[0] for word in profile.name.split()[:2])
                st.markdown(f"<div class='crew-card'><div class='crew-avatar'>{escape(initials)}</div><div><div class='crew-name'>{escape(profile.name)}</div><div class='crew-role'>{escape(profile.role or 'Mission profile')} · {escape(profile.mission_id)}</div></div></div>",unsafe_allow_html=True)
        trends,events=st.columns([2.6,1])
        with trends:
            section_heading('Physiological trajectory','PERSONAL HISTORY')
            metric=st.selectbox('Indicator',sorted(ALLOWED_METRICS),index=sorted(ALLOWED_METRICS).index('heart_rate'),key='dashboard_metric')
            view=metric_view(session,astronaut.id,metric)
            if view['history'].empty:st.info('No observations for this signal. Register one in Data Management.')
            else:st.plotly_chart(history_figure(view),key='overview_history',width='stretch')
        with events:
            section_heading('Mission log','RECENT EVENTS')
            events=get_mission_events(session)
            if not events:st.info('No mission events recorded.')
            for event in events[-4:][::-1]:
                st.markdown(f"<div class='event-row'><div class='event-time'>{event.timestamp:%d %b · %H:%M} UTC</div><div class='event-title'>{escape(event.event_type)}</div><div class='crew-role'>{escape(event.description)}</div></div>",unsafe_allow_html=True)
            navigation_button('Generate mission report','Mission Reports','overview_report',':material/picture_as_pdf:')
        with st.expander('Data provenance and interpretation'):
            st.write(result['quality']['sources']);st.caption(result['limitations'])


def render_health_dashboard():
    apply_theia_theme()
    render_page_header('Health Intelligence','Personal variation, observed trends and transparent evidence.')
    with SessionLocal() as session:
        astronaut=ensure_astronaut(session)
        frame=measurement_frame(session,astronaut.id)
        period=st.segmented_control('Observation window',['7 days','30 days','90 days','All records'],default='All records',key='health_period')
        cutoff=None if period in {None,'All records'} else datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=int(period.split()[0]))
        result=analyze(session,astronaut.id,start=cutoff)
        metrics=result['metrics']
        columns=st.columns(4)
        for column,label,value,detail,tone in zip(columns,['OBSERVATIONS','ANALYZED SIGNALS','STATISTICAL FLAGS','EXCLUDED'],[result['quality']['total'],len(metrics),sum(len(item['anomalies']) for item in metrics.values()),result['quality']['excluded']],['Selected period','Separate source cohorts','Review with context','Validation checks'],['cyan','green','violet','amber']):
            with column:info_card(label,value,detail,tone)
        metric=st.selectbox('Health indicator',sorted(ALLOWED_METRICS),index=sorted(ALLOWED_METRICS).index('heart_rate'),key='health_metric')
        plot,baseline=st.columns([2.4,1])
        with plot:
            section_heading('Signal history','HOVER · ZOOM · COMPARE')
            view=render_analysis(session,astronaut.id,metric,'health',start=cutoff)
        with baseline:
            section_heading('Period distribution','RETROSPECTIVE / NOT INDEPENDENT BASELINE')
            for item in view['baselines']:
                info_card(item['cohort'].upper(),f"{item['mean']:.2f} {item['unit']}",f"Mean · {item['samples']} samples")
                st.metric('Variability / standard deviation',f"{item['std']:.3f}")
                st.metric('Median',f"{item['median']:.3f}")
                st.caption(item['status'])
                if cutoff is not None:
                    previous_start=cutoff-(datetime.now(timezone.utc).replace(tzinfo=None)-cutoff)
                    previous=analyze(session,astronaut.id,start=previous_start,end=cutoff-timedelta(microseconds=1))
                    prior=previous['metrics'].get(f"{metric}:{item['cohort']}")
                    if prior:st.metric('Mean change vs previous period',f"{item['mean']-prior['mean']:+.3f} {item['unit']}")
                    else:st.caption('No comparable observations in the previous period.')
            if not view['baselines']:st.info('A baseline appears when valid measurements are available.')
