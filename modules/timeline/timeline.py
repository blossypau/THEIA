from __future__ import annotations

from html import escape
import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.repository import ensure_astronaut
from database.models import MissionEvent
from database.repository import get_mission_events
from modules.ui.theme import apply_theia_theme, render_page_header


def render_timeline() -> None:
    apply_theia_theme()
    render_page_header("Mission timeline", "System events • workload markers • crew activity chronology")

    session = SessionLocal()
    try:
        from services.mission_timeline import timeline_events
        events=timeline_events(session,ensure_astronaut(session).id)
        if events:
            categories=st.multiselect('Recorded event categories',sorted({r['kind'] for r in events}),key='timeline_categories')
            filtered=[r for r in events if not categories or r['kind'] in categories]
            st.caption(f'{len(filtered)} recorded items. Latest 300 shown; no unrecorded exposure or sleep period is inferred.')
            if filtered:
                choices=filtered[-300:]
                selected=st.selectbox('Inspect recorded event',range(len(choices)),format_func=lambda i:f"{choices[i]['timestamp']} / {choices[i]['source']} / {choices[i]['title']}",key='timeline_event')
                item=choices[selected]
                st.write(item['title']);st.json(item['details'])
                st.dataframe([{k:v for k,v in r.items() if k!='details'} for r in choices],hide_index=True)
            else:st.info('No events match the current filters.')
        else:st.info('No mission events or observations recorded yet.')

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        with st.form("add_event"):
            event_type = st.text_input("Event type")
            description = st.text_area("Description")
            mission_day = st.number_input("Mission day", min_value=0, step=1)
            submitted = st.form_submit_button("Add event")

        if submitted:
            event = MissionEvent(
                astronaut_id=ensure_astronaut(session).id,
                event_type=event_type or "General",
                description=description or "Manual mission event",
                mission_day=int(mission_day),
            )
            session.add(event)
            session.commit()
            st.success("Mission event added.")
    finally:
        session.close()
