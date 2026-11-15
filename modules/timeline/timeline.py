from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.models import MissionEvent
from database.repository import get_mission_events
from modules.ui.theme import apply_theia_theme, render_page_header


def render_timeline() -> None:
    apply_theia_theme()
    render_page_header("Mission timeline", "System events • workload markers • crew activity chronology")

    session = SessionLocal()
    try:
        events = get_mission_events(session)
        if events:
            event_type_filter = st.multiselect("Filter by event type", sorted({event.event_type for event in events}), default=[])
            filtered = [event for event in events if not event_type_filter or event.event_type in event_type_filter]
            if not filtered:
                st.info("No events match the current filter selection.")
                return

            st.markdown("<div class='section-tag'>Chronology</div>", unsafe_allow_html=True)
            for event in filtered:
                st.markdown(
                    f"""
                    <div class='timeline-item'>
                        <div class='timeline-mark'></div>
                        <div class='timeline-content'>
                            <div class='timeline-title'>{event.event_type}</div>
                            <div class='timeline-subtitle'>Mission day {event.mission_day} • {event.timestamp.strftime('%Y-%m-%d %H:%M')}</div>
                            <div style='color: var(--text); margin-top: 0.18rem;'>{event.description}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
            rows = [{
                "Mission Day": event.mission_day,
                "Type": event.event_type,
                "Description": event.description,
                "Timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M")
            } for event in filtered]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No mission events recorded yet.")

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
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
