from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
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
            notes = st.text_area("General observations")
            symptoms = st.text_area("Optional symptoms")

            progress = sum(value > 0 for value in [sleep_duration, sleep_quality, mood, energy, fatigue, effort])
            st.progress(progress / 6)
            submitted = st.form_submit_button("Save check-in")

        if submitted:
            checkin = DailyCheckin(
                astronaut_id=1,
                mission_day=128,
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
            st.dataframe(pd.DataFrame(records), use_container_width=True)
        else:
            st.info("No check-ins recorded yet.")
    finally:
        session.close()
