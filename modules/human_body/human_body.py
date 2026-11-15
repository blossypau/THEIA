from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

from database.database import SessionLocal
from database.repository import get_measurements_for_metric


SYSTEMS = {
    "Cardiovascular": ["heart_rate", "blood_pressure", "oxygen_saturation"],
    "Musculoskeletal": ["exercise", "fatigue", "energy"],
    "Metabolic": ["blood_glucose", "energy", "nutrition"],
    "Neurological and vestibular": ["sleep_hours", "mood", "fatigue"],
    "Thermoregulation": ["body_temperature", "sleep_hours"],
    "Psychological and behavioral wellbeing": ["mood", "fatigue", "energy"],
}


def render_human_body():
    st.subheader("Interactive Human Body")
    system = st.radio("Select a body system", list(SYSTEMS.keys()))

    body_svg = f"""
    <svg width="220" height="360" viewBox="0 0 220 360" xmlns="http://www.w3.org/2000/svg">
      <rect width="220" height="360" fill="#0b1725" rx="20"/>
      <circle cx="110" cy="52" r="28" fill="#b08cff" opacity="0.9"/>
      <rect x="78" y="90" width="64" height="90" rx="18" fill="#2f3a4d"/>
      <rect x="60" y="95" width="18" height="110" rx="8" fill="#2f3a4d"/>
      <rect x="142" y="95" width="18" height="110" rx="8" fill="#2f3a4d"/>
      <rect x="82" y="180" width="22" height="90" rx="8" fill="#3a4b62"/>
      <rect x="116" y="180" width="22" height="90" rx="8" fill="#3a4b62"/>
      <rect x="88" y="270" width="18" height="86" rx="8" fill="#566c89"/>
      <rect x="114" y="270" width="18" height="86" rx="8" fill="#566c89"/>
      <circle cx="110" cy="155" r="6" fill="#6fe7ff" opacity="0.9"/>
      <text x="110" y="330" text-anchor="middle" fill="#e7f3ff" font-size="18" font-family="sans-serif">{system}</text>
    </svg>
    """
    html(body_svg, height=400)

    st.write("### Relevant indicators")
    session = SessionLocal()
    try:
        indicators = []
        for metric in SYSTEMS[system]:
            if metric in {"exercise", "nutrition"}:
                continue
            row = get_measurements_for_metric(session, metric)
            if row:
                latest = row[-1]
                indicators.append((metric, latest.value, latest.unit, latest.timestamp))
        if indicators:
            for metric, value, unit, ts in indicators:
                st.write(f"- {metric.replace('_', ' ').title()}: {value} {unit} at {ts}")
        else:
            st.info("No direct measurement history available for this system yet.")

        st.write("### Educational explanation")
        hazard_map = {
            "Cardiovascular": "Exercise strain, hydration shifts, and cabin environmental changes can alter cardiovascular responses.",
            "Musculoskeletal": "Exercise load, recovery time, and sleep quality influence tissue stress and muscle fatigue.",
            "Metabolic": "Meal timing, hydration, and workload all affect glucose stability and sustained energy.",
            "Neurological and vestibular": "Sleep disruption, workload changes, and microgravity adaptation can influence perception and alertness.",
            "Thermoregulation": "Thermal environment, exertion, and sleep quality affect body temperature regulation.",
            "Psychological and behavioral wellbeing": "Mood, workload, social engagement, and rest needs shape wellbeing over time.",
        }
        st.info(hazard_map[system])

        st.write("### Preventive guidance")
        guidance = {
            "Cardiovascular": "Review recovery periods and hydration after exercise. If unusual dizziness or sustained elevated heart rate occurs, contact the authorized medical team.",
            "Musculoskeletal": "Prioritize progressive load management, mobility, and sleep to protect musculoskeletal integrity.",
            "Metabolic": "Maintain regular meal timing and hydration while tracking energy trends and glucose stability.",
            "Neurological and vestibular": "Protect sleep quality and note any sensory changes promptly; do not ignore persistent imbalance symptoms.",
            "Thermoregulation": "Review thermal comfort, hydration, and workload balance when temperature shifts appear.",
            "Psychological and behavioral wellbeing": "Use check-ins, crew support, and rest planning to monitor mood and fatigue trends.",
        }
        st.success(guidance[system])
    finally:
        session.close()
