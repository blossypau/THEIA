from __future__ import annotations

import streamlit as st

from database.database import SessionLocal
from database.models import DailyCheckin, ExerciseRecord, MissionEvent


def render_gamification():
    st.subheader("Wellbeing & Crew Collaboration")
    session = SessionLocal()
    try:
        checkins = session.query(DailyCheckin).count()
        exercise_sessions = session.query(ExerciseRecord).count()
        mission_events = session.query(MissionEvent).count()

        st.metric("Daily check-ins completed", checkins)
        st.metric("Exercise sessions recorded", exercise_sessions)
        st.metric("Mission events logged", mission_events)

        st.write("### Preventive wellbeing activities")
        progress = [
            ("Hydration check", 80),
            ("Recovery planning", 75),
            ("Exercise readiness", 67),
            ("Crew wellbeing challenge", 90),
        ]
        for label, value in progress:
            st.progress(value / 100)
            st.caption(f"{label}: {value}%")

        st.write("### Crew objectives")
        st.markdown("- Complete daily check-ins to maintain a recovery-focused routine.")
        st.markdown("- Log exercise sessions with hydration and rest notes.")
        st.markdown("- Participate in learning modules without compromising sleep quality or fatigue awareness.")
    finally:
        session.close()
