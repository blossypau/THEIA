from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from config.settings import ROOT_DIR


def render_health_guidance():
    st.subheader("Health Guidance Library")
    path = ROOT_DIR / "config" / "health_rules.json"
    with path.open("r", encoding="utf-8") as file:
        entries = json.load(file)

    for entry in entries:
        with st.container():
            st.markdown(f"### {entry['topic']}")
            st.write(f"Body system: {entry['body_system']}")
            st.write(f"Related indicators: {', '.join(entry['related_indicators'])}")
            st.write(f"Explanation: {entry['explanation']}")
            st.write(f"Preventive information: {entry['preventive_info']}")
            st.caption(f"Source: {entry['source']} | Last reviewed: {entry['last_review_date']}")
            st.markdown("---")
