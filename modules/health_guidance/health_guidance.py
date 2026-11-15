from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from config.settings import ROOT_DIR


def render_health_guidance():
    st.caption("Educational guidance library / actions are self-reported")
    st.caption("Action-oriented tasks to improve daily health and reduce isolation risk during mission operations.")

    from database.database import SessionLocal
    from database.repository import ensure_astronaut
    from intelligence.historical import historical_analysis
    from services.space_context import hazard_inventory
    with SessionLocal() as session:
        profile=ensure_astronaut(session)
        review=historical_analysis(session,profile.id)
        st.subheader('Evidence review, not treatment')
        for item in review['signals']:
            changed=[r for r in item['observations'] if r['flagged']]
            if changed:
                st.write(item['metric'],item['source'],changed)
                st.caption(f"Method: {item['method']} / {item['samples']} prior samples on {item['days']} observed days. Reference before {item['reference_before']}.")
        st.info('Review questions: Were units and timestamps correct? Is the source verified? Did posture, activity, device or recording protocol change? Are days missing? Statistical change alone does not identify a cause.')
        st.caption('For material findings, involve qualified mission/research or healthcare staff. THEIA supplies no treatment, psychological diagnosis or autonomous operational decision.')
        for name,context in hazard_inventory(session,profile.id).items():
            with st.expander(name):
                st.write(context['note']);st.caption(f"Recorded context: {context['context_records']} / sources: {context['recorded_sources']}")
                st.link_button('NASA research context',context['url'])
    path = ROOT_DIR / "config" / "health_rules.json"
    with path.open("r", encoding="utf-8") as file:
        entries = json.load(file)

    for index, entry in enumerate(entries):
        with st.container():
            priority = "Educational"
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, rgba(14,116,144,0.16), rgba(15,23,42,0.75)); border: 1px solid rgba(125,211,252,0.38); border-radius: 18px; padding: 1rem; margin-bottom: 1rem;">
                  <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                    <h3 style="margin: 0; color: #F8FAFC;">{entry['topic']}</h3>
                    <span style="padding: 0.35rem 0.7rem; border-radius: 999px; background: rgba(45,212,191,0.12); color: #A7F3D0; border: 1px solid rgba(45,212,191,0.5); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em;">{priority} resource</span>
                  </div>
                  <p style="margin: 0.25rem 0; color: #E2E8F0;"><strong>Body system:</strong> {entry['body_system']}</p>
                  <p style="margin: 0.25rem 0; color: #E2E8F0;"><strong>Focus indicators:</strong> {', '.join(entry['related_indicators'])}</p>
                  <p style="margin: 0.25rem 0; color: #E2E8F0;"><strong>Task:</strong> {entry['preventive_info']}</p>
                  <p style="margin: 0.25rem 0; color: #E2E8F0;"><strong>Why this matters:</strong> {entry['explanation']}</p>
                  <p style="margin: 0.35rem 0 0; color: #A5F3FC; font-size: 0.8rem;">Source: {entry['source']} • Reviewed {entry['last_review_date']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.checkbox(f"Mark task: {entry['topic']}", key=f"guidance_task_{index}")
            st.markdown("---")
