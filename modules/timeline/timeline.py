from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.models import MissionEvent
from database.repository import get_mission_events


def render_timeline():
    st.subheader("Mission Timeline")
    session = SessionLocal()
    try:
        events = get_mission_events(session)
        if events:
            rows = [{
                "Mission Day": event.mission_day,
                "Type": event.event_type,
                "Description": event.description,
                "Timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M")
            } for event in events]
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No mission events recorded yet.")

        st.markdown("---")
        with st.form("add_event"):
            event_type = st.text_input("Event type")
            description = st.text_area("Description")
            mission_day = st.number_input("Mission day", min_value=0, step=1)
            submitted = st.form_submit_button("Add event")

        if submitted:
            event = MissionEvent(
                astronaut_id=1,
                event_type=event_type or "General",
                description=description or "Manual mission event",
                mission_day=int(mission_day),
            )
            session.add(event)
            session.commit()
            st.success("Mission event added.")
    finally:
        session.close()
