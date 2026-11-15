from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.repository import ensure_astronaut
from database.models import DailyCheckin
from database.repository import get_daily_checkins
from modules.ui.theme import apply_theia_theme, render_page_header


def render_daily_checkin() -> None:
    apply_theia_theme()
    render_page_header("Daily check-in", "Behavioral readiness • rest quality • mission self-reporting")

    session = SessionLocal()
    try:
        with st.form("daily_checkin_form"):
            st.markdown("<div class='section-tag'>Mission self-report</div>", unsafe_allow_html=True)
            sleep_duration = st.number_input("Sleep duration (hours)", min_value=0.0, max_value=18.0, step=0.5, value=7.5)
            sleep_quality = st.slider("Sleep quality (1-5)", 1, 5, 3)
            mood = st.slider("Mood (0-100)", 0, 100, 72)
            energy = st.slider("Energy (0-100)", 0, 100, 68)
            fatigue = st.slider("Fatigue (0-100)", 0, 100, 28)
            effort = st.slider("Perceived physical effort (0-100)", 0, 100, 44)
            workload=st.slider('Perceived workload (0-100)',0,100,40)
            stress=st.slider('Voluntary perceived stress (0-100)',0,100,30)
            social_consent=st.checkbox('Voluntarily log social interaction minutes')
            social=st.number_input('Voluntary social minutes',min_value=0.,value=0.) if social_consent else None
            sleep_start=st.number_input('Reported rest start hour (UTC, 0-23.99)',min_value=0.,max_value=23.99,value=22.)
            sleep_end=st.number_input('Reported rest end hour (UTC, 0-23.99)',min_value=0.,max_value=23.99,value=6.)
            st.caption('Self-reports are not diagnostic scales. Social logging is optional. No camera or voice inference is used.')
            notes = st.text_area("General observations")
            symptoms = st.text_area("Optional symptoms")

            progress = sum(value > 0 for value in [sleep_duration, sleep_quality, mood, energy, fatigue, effort])
            st.progress(progress / 6)
            submitted = st.form_submit_button("Save check-in")

        if submitted:
            checkin = DailyCheckin(
                astronaut_id=ensure_astronaut(session).id,
                mission_day=ensure_astronaut(session).mission_day,
                sleep_duration_hours=float(sleep_duration),
                sleep_quality=int(sleep_quality),
                mood=int(mood),
                energy=int(energy),
                fatigue=int(fatigue),
                effort=int(effort),
                general_observations=notes,
                symptoms=symptoms,
            )
            session.add(checkin)
            session.flush()
            from database.measurements import insert_measurement
            for metric, value, unit in [("sleep_hours", sleep_duration, "hours"), ("mood", mood, "score"), ("energy", energy, "score"), ("fatigue", fatigue, "score")]:
                insert_measurement(session, checkin.astronaut_id, dict(metric_name=metric, value=value, unit=unit, timestamp=checkin.timestamp, source="MANUALLY_ENTERED_DATA", mission_context="Daily check-in"), commit=False)
            from services.space_context import add_context
            context=[('workload_score',workload),('stress_score',stress),('sleep_start_hour',sleep_start),('sleep_end_hour',sleep_end)]
            if social is not None:context.append(('social_minutes',social))
            for name,value in context:
                add_context(session,checkin.astronaut_id,dict(kind='wellbeing',timestamp=checkin.timestamp,
                    source='SIMULATED_DATA' if session.info.get('scenario') else 'MANUALLY_ENTERED_DATA',instrument='Voluntary self-report',
                    payload={'metric':name,'value':value,'consent':social_consent}),commit=False)
            session.commit()
            st.success("Daily check-in saved and added to mission history.")

        checkins = get_daily_checkins(session)
        if checkins:
            records = [{
                "Mission Day": item.mission_day,
                "Sleep Hours": item.sleep_duration_hours,
                "Sleep Quality": item.sleep_quality,
                "Mood": item.mood,
                "Energy": item.energy,
                "Fatigue": item.fatigue,
                "Timestamp": item.timestamp.strftime("%Y-%m-%d %H:%M")
            } for item in checkins]
            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(records), width="stretch")
        else:
            st.info("No check-ins recorded yet.")
    finally:
        session.close()
