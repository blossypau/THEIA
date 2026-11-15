from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.models import DailyCheckin
from database.repository import get_daily_checkins


def render_daily_checkin():
    st.subheader("Daily Check-In")
    session = SessionLocal()
    try:
        with st.form("daily_checkin_form"):
            st.write("Record your daily status")
            sleep_duration = st.number_input("Sleep duration (hours)", min_value=0.0, max_value=18.0, step=0.5)
            sleep_quality = st.slider("Sleep quality (1-5)", 1, 5, 3)
            mood = st.slider("Mood (0-100)", 0, 100, 60)
            energy = st.slider("Energy (0-100)", 0, 100, 65)
            fatigue = st.slider("Fatigue (0-100)", 0, 100, 25)
            effort = st.slider("Perceived physical effort (0-100)", 0, 100, 40)
            notes = st.text_area("General observations")
            symptoms = st.text_area("Optional symptoms")
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
            st.success("Daily check-in saved.")

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
            st.dataframe(pd.DataFrame(records), use_container_width=True)
        else:
            st.info("No check-ins recorded yet.")
    finally:
        session.close()
