from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.repository import ensure_astronaut
from database.models import MissionContext
from database.repository import get_context_records


def render_mission_context():
    st.subheader("Mission Context Engine")
    session = SessionLocal()
    try:
        with st.form("mission_context_form"):
            mission_day = st.number_input("Mission day", min_value=0, step=1)
            phase = st.selectbox("Mission phase", ["Routine", "EVA", "Exercise", "Recovery", "Crew transfer", "Medical review"])
            activity = st.text_area("Recent physical activity")
            workouts = st.text_area("Exercise sessions")
            eva = st.text_area("EVA activities")
            sleep = st.text_area("Sleep history")
            nutrition = st.text_area("Nutrition")
            environment = st.text_area("Environmental observations")
            events = st.text_area("Relevant mission events")
            submitted = st.form_submit_button("Save context")

        if submitted:
            entry = MissionContext(
                astronaut_id=ensure_astronaut(session).id,
                mission_day=int(mission_day),
                phase=phase,
                recent_physical_activity=activity,
                exercise_sessions=workouts,
                eva_activities=eva,
                sleep_history=sleep,
                nutrition=nutrition,
                environmental_observations=environment,
                relevant_events=events,
            )
            session.add(entry)
            session.commit()
            st.success("Mission context saved.")

        records = get_context_records(session)
        if records:
            df = pd.DataFrame([
                {
                    "Mission Day": item.mission_day,
                    "Phase": item.phase,
                    "Recent Activity": item.recent_physical_activity,
                    "Sleep History": item.sleep_history,
                    "Events": item.relevant_events,
                    "Timestamp": item.timestamp.strftime("%Y-%m-%d %H:%M")
                }
                for item in records
            ])
            st.dataframe(df, width="stretch")
    finally:
        session.close()
