from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import SessionLocal
from database.repository import get_measurements_for_metric
from modules.ui.theme import apply_theia_theme, render_page_header


SYSTEMS = {
    "Cardiovascular": {
        "metrics": ["heart_rate", "blood_pressure", "body_temperature"],
        "organs": {
            "Heart": "The heart pumps oxygen-rich blood through the circulation and is a key performance marker during exercise and recovery.",
            "Lungs": "The lungs exchange oxygen and carbon dioxide and support cardiovascular efficiency under mission load.",
            "Aorta": "The aorta distributes blood from the heart to systemic circulation and reflects central hemodynamic status.",
        },
    },
    "Respiratory": {
        "metrics": ["oxygen_saturation", "body_temperature", "sleep_hours"],
        "organs": {
            "Lungs": "The lungs regulate gas exchange and are highly relevant to oxygenation and recovery during stress.",
            "Airway": "Airway function supports respiratory flow, oxygen delivery, and thermal exchange in enclosed habitats.",
            "Diaphragm": "The diaphragm supports ventilation and can be affected by fatigue, posture, and respiratory strain.",
        },
    },
    "Nervous": {
        "metrics": ["sleep_hours", "mood", "fatigue"],
        "organs": {
            "Brain": "The brain coordinates perception, cognition, and adaptive responses to mission stressors.",
            "Spinal Cord": "The spinal cord relays information between the brain and the body and supports postural control.",
            "Cerebellum": "The cerebellum supports coordination, balance, and fine motor control in daily mission activity.",
        },
    },
    "Musculoskeletal": {
        "metrics": ["fatigue", "sleep_hours", "mood"],
        "organs": {
            "Skeleton": "The skeleton provides support, protection, and mechanical leverage during physical mission tasks.",
            "Muscles": "Muscle readiness is central to exercise tolerance, strength maintenance, and recovery quality.",
            "Joints": "Joint integrity and comfort affect the ability to perform crew tasks and maintain mobility.",
        },
    },
    "Digestive": {
        "metrics": ["blood_glucose", "body_temperature", "sleep_hours"],
        "organs": {
            "Liver": "The liver supports nutrient processing, detoxification, and energy storage relevant to mission nutrition.",
            "Stomach": "The stomach supports digestion and intake timing, which affects energy availability and comfort.",
            "Intestines": "The intestines absorb nutrients and contribute to gastro-intestinal resilience during spaceflight.",
        },
    },
    "Endocrine": {
        "metrics": ["blood_glucose", "mood", "sleep_hours"],
        "organs": {
            "Pancreas": "The pancreas supports glucose regulation and endocrine balance relevant to metabolism and energy shifts.",
            "Thyroid": "The thyroid influences metabolic activity and energy use over time.",
            "Adrenal Glands": "The adrenal glands contribute to stress response and recovery dynamics in demanding mission settings.",
        },
    },
    "Urinary": {
        "metrics": ["body_temperature", "sleep_hours", "blood_glucose"],
        "organs": {
            "Kidneys": "The kidneys regulate fluid balance and filtration, which are vital in constrained habitat conditions.",
            "Bladder": "The bladder stores and releases fluid, providing a useful indicator of hydration status and patterns.",
            "Urinary Tract": "The urinary tract supports fluid balance and contributes to systemic homeostasis.",
        },
    },
    "Integumentary": {
        "metrics": ["body_temperature", "sleep_hours", "mood"],
        "organs": {
            "Skin": "The skin protects against radiation, abrasion, and thermal fluctuations in the mission environment.",
            "Sweat Glands": "Sweat glands support thermoregulation during exertion and environmental stress.",
            "Hair and Nails": "Hair and nails reflect general tissue health and continuity under long-duration mission conditions.",
        },
    },
}

SYSTEM_COLORS = {
    "Cardiovascular": "#7dd3fc",
    "Respiratory": "#2dd4bf",
    "Nervous": "#c084fc",
    "Musculoskeletal": "#fbbf24",
    "Digestive": "#fb7185",
    "Endocrine": "#f9a8d4",
    "Urinary": "#a7f3d0",
    "Integumentary": "#fca5a5",
}

VIEW_OVERLAYS = {
    "Anatomical": "<ellipse cx='210' cy='232' rx='125' ry='170' fill='rgba(94,234,212,0.08)' stroke='rgba(94,234,212,0.45)' stroke-width='2' />",
    "X-ray": "<path d='M110 90 Q210 55 310 90 L300 420 Q210 485 120 420 Z' fill='rgba(148,163,184,0.10)' stroke='rgba(148,163,184,0.85)' stroke-width='2' fill-opacity='0.8' />",
    "Regional": "<g><circle cx='210' cy='240' r='95' fill='rgba(125,211,252,0.08)' stroke='rgba(125,211,252,0.7)' stroke-width='2' /><circle cx='210' cy='240' r='140' fill='none' stroke='rgba(125,211,252,0.4)' stroke-width='1.5' stroke-dasharray='6 8' /></g>",
    "Isolated": "<g><circle cx='210' cy='240' r='12' fill='rgba(255,255,255,0.85)' stroke='rgba(94,234,212,0.9)' stroke-width='2' /><circle cx='210' cy='240' r='64' fill='none' stroke='rgba(255,255,255,0.5)' stroke-width='1.5'/></g>",
}

ORGAN_HOTSPOTS = {
    "Heart": [(210, 140)],
    "Lungs": [(170, 145), (250, 145)],
    "Aorta": [(210, 168)],
    "Airway": [(170, 125), (250, 125)],
    "Diaphragm": [(210, 210)],
    "Brain": [(210, 90)],
    "Spinal Cord": [(210, 180)],
    "Cerebellum": [(210, 108)],
    "Skeleton": [(210, 220)],
    "Muscles": [(170, 260), (250, 260)],
    "Joints": [(170, 310), (250, 310)],
    "Liver": [(210, 250)],
    "Stomach": [(210, 225)],
    "Intestines": [(210, 300)],
    "Pancreas": [(210, 210)],
    "Thyroid": [(210, 118)],
    "Adrenal Glands": [(170, 240), (250, 240)],
    "Kidneys": [(170, 285), (250, 285)],
    "Bladder": [(210, 350)],
    "Urinary Tract": [(210, 325)],
    "Skin": [(210, 340)],
    "Sweat Glands": [(170, 260), (250, 260)],
    "Hair and Nails": [(210, 15)],
}


def _system_description(system: str) -> str:
    mapping = {
        "Cardiovascular": "Cardiovascular performance is reviewed in relation to workload, hydration, and thermal stress. Stable heart rate and blood pressure patterns support robust recovery during constrained mission operations.",
        "Respiratory": "Respiratory function supports oxygen delivery, carbon dioxide clearance, and adaptation to environmental stressors, including reconfigurable habitat conditions.",
        "Nervous": "Sleep quality, fatigue, and mood strongly influence alertness, coordination, and the ability to maintain performance during long mission periods.",
        "Musculoskeletal": "Muscular and skeletal readiness respond to exercise load, recovery periods, and sleep quality. Monitoring workload helps preserve strength and positional stability.",
        "Digestive": "Digestive and metabolic support affects nutrient intake, energy availability, and crew resilience in closed environments.",
        "Endocrine": "Endocrine activity shapes energy regulation, stress adaptation, and metabolic balance over extended mission operations.",
        "Urinary": "Fluid regulation and renal function are essential for overall homeostasis, especially when hydration and habitat conditions vary.",
        "Integumentary": "Skin and thermoregulatory function protect the body from environmental extremes and help maintain thermal stability.",
    }
    return mapping[system]


def _get_organ_metadata(organ_name: str, system: str) -> dict[str, Any]:
    system_map = SYSTEMS.get(system, {})
    organ_summary = system_map.get("organs", {}).get(organ_name, "Educational structure overview.")
    if organ_name == "Heart":
        return {
            "system": "Cardiovascular",
            "function": "Pumps blood through the pulmonary and systemic circulations.",
            "description": "The heart is a muscular organ responsible for circulating oxygenated blood to tissues and returning deoxygenated blood to the lungs.",
            "astronaut_context": "Cardiovascular data provides a view of workload, recovery, and adaptation during exercise, sleep loss, or environmental stress.",
            "resources": ["Cardiovascular education", "Mission context review", "Recent heart-rate history"],
        }
    if organ_name == "Brain":
        return {
            "system": "Nervous",
            "function": "Coordinates perception, cognition, and sensorimotor response.",
            "description": "The brain integrates sensory input and manages thought, memory, movement, and homeostatic control.",
            "astronaut_context": "Changes in sleep, fatigue, and mood can influence performance, attention, and cognitive readiness during a mission.",
            "resources": ["Cognitive readiness brief", "Rest quality review", "Mission workload notes"],
        }
    if organ_name == "Lungs":
        return {
            "system": "Respiratory",
            "function": "Exchange oxygen and carbon dioxide between blood and air.",
            "description": "The lungs support gas exchange and are essential for metabolic efficiency and sustained activity at altitude and in enclosed habitats.",
            "astronaut_context": "Oxygenation trends and thermal burden are relevant when evaluating respiratory load and recovery quality.",
            "resources": ["Respiratory system overview", "Oxygenation trend review", "Ventilation context"],
        }
    if organ_name == "Liver":
        return {
            "system": "Digestive",
            "function": "Processes nutrients, stores energy, and supports detoxification pathways.",
            "description": "The liver has a central role in metabolism and nutrient management, helping to maintain energy balance.",
            "astronaut_context": "This organ relates to nutrition timing, energy availability, and broader metabolic resilience.",
            "resources": ["Metabolism overview", "Nutritional context", "Energy balance notes"],
        }
    if organ_name == "Kidneys":
        return {
            "system": "Urinary",
            "function": "Filter blood and regulate fluid balance and waste elimination.",
            "description": "The kidneys regulate water, electrolytes, and waste excretion, contributing to stable systemic function.",
            "astronaut_context": "Hydration, workload, and thermal load can influence the interpretation of urine-related and fluid-balance patterns.",
            "resources": ["Fluid regulation overview", "Hydration context", "Environmental stress notes"],
        }
    if organ_name == "Skin":
        return {
            "system": "Integumentary",
            "function": "Provides barrier protection and helps regulate body temperature.",
            "description": "The skin supports thermal regulation, environmental protection, and sensory feedback from the external environment.",
            "astronaut_context": "Changes in skin condition and thermoregulation can be relevant during periods of thermal stress or elevated exertion.",
            "resources": ["Thermal regulation overview", "Environmental exposure notes", "Recovery evaluation"],
        }
    return {
        "system": system,
        "function": "Supports the role of the selected organ in preserving mission health.",
        "description": organ_summary,
        "astronaut_context": "This anatomy view connects educational context with the astronaut’s current measurement patterns and mission notes.",
        "resources": ["System overview", "Measurement review", "Mission timeline"],
    }


def _render_organ_svg(system: str, selected_organ: str, view_mode: str) -> str:
    system_color = SYSTEM_COLORS.get(system, "#8b5cf6")
    opacity = 0.28 if view_mode == "X-ray" else 0.7
    highlight_positions = ORGAN_HOTSPOTS.get(selected_organ, [(210, 210)])
    overlay = VIEW_OVERLAYS.get(view_mode, VIEW_OVERLAYS["Anatomical"])

    hotspots = "".join(
        f"<circle cx='{x}' cy='{y}' r='{12 if len(highlight_positions) == 1 else 9}' fill='#ffffff' opacity='0.96' stroke='white' stroke-width='2'/>"
        for x, y in highlight_positions
    )

    body_shell = f"""
    <svg width='100%' height='520' viewBox='0 0 420 520' xmlns='http://www.w3.org/2000/svg'>
      <defs>
        <linearGradient id='bodyGrad' x1='0' x2='1'>
          <stop offset='0%' stop-color='{system_color}' stop-opacity='0.95'/>
          <stop offset='100%' stop-color='#5eead4' stop-opacity='0.75'/>
        </linearGradient>
      </defs>
      <rect width='420' height='520' fill='rgba(9, 14, 24, 0.78)' rx='24'/>
      <g opacity='{opacity}'>
        <circle cx='210' cy='80' r='36' fill='url(#bodyGrad)' opacity='0.9'/>
        <ellipse cx='210' cy='138' rx='62' ry='82' fill='rgba(124, 58, 237, 0.28)' stroke='rgba(178, 167, 255, 0.9)' stroke-width='3'/>
        <rect x='163' y='180' width='94' height='120' rx='26' fill='rgba(124, 58, 237, 0.18)' stroke='rgba(178, 167, 255, 0.7)' stroke-width='2.5'/>
        <path d='M172 240 L130 316 L158 444 L191 390 L191 240 Z' fill='rgba(94, 234, 212, 0.14)' stroke='rgba(94, 234, 212, 0.7)' stroke-width='3'/>
        <path d='M248 240 L290 316 L262 444 L229 390 L229 240 Z' fill='rgba(94, 234, 212, 0.14)' stroke='rgba(94, 234, 212, 0.7)' stroke-width='3'/>
        <path d='M200 180 L170 240 L181 450 L200 492 L220 450 L230 240 L210 180 Z' fill='rgba(124, 58, 237, 0.16)' stroke='rgba(178, 167, 255, 0.75)' stroke-width='3'/>
      </g>
      {overlay}
      <g>
        {hotspots}
      </g>
      <g>
        <rect x='28' y='18' width='150' height='30' rx='15' fill='rgba(15, 23, 42, 0.6)' stroke='rgba(125,211,252,0.5)' />
        <text x='42' y='38' fill='#ecfeff' font-size='14' font-family='Inter, sans-serif' font-weight='600'>{system}</text>
      </g>
      <text x='210' y='495' text-anchor='middle' fill='#F8FAFC' font-family='Inter, sans-serif' font-size='17' font-weight='700'>{selected_organ}</text>
    </svg>
    """
    return body_shell


def render_human_body() -> None:
    apply_theia_theme()
    render_page_header("Human body explorer", "Interactive systems review • scientific context • astronaut data correlation")

    system_names = list(SYSTEMS.keys())
    system = st.segmented_control("Select body system", system_names, default=system_names[0], selection_mode="single")
    available_organs = list(SYSTEMS[system]["organs"].keys())
    selected_organ = st.selectbox("Select structure", available_organs, index=0)
    view_mode = st.pills("View mode", ["Anatomical", "X-ray", "Regional", "Isolated"], selection_mode="single", default="Anatomical")

    st.markdown(
        """
        <style>
        .holo-body-panel {
            background: linear-gradient(135deg, rgba(10,18,32,0.9), rgba(18,32,44,0.82));
            border: 1px solid rgba(125, 211, 252, 0.35);
            border-radius: 24px;
            padding: 1rem;
            box-shadow: 0 18px 48px rgba(12, 20, 35, 0.35);
        }
        .body-stage {
            display: grid;
            grid-template-columns: 1.25fr 0.75fr;
            gap: 1rem;
        }
        .data-card {
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 18px;
            padding: 1rem;
        }
        .section-pill {
            display: inline-block;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            background: rgba(94, 234, 212, 0.1);
            border: 1px solid rgba(94, 234, 212, 0.35);
            color: #d9fafe;
            font-size: 0.7rem;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }
        .atlas-inline-metrics {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.5rem 0 1rem 0;
        }
        .atlas-chip {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 999px;
            padding: 0.3rem 0.7rem;
            font-size: 0.75rem;
            color: #E2E8F0;
        }
        .mission-story {
            background: rgba(15, 23, 42, 0.65);
            border-left: 3px solid rgba(125, 211, 252, 0.8);
            padding: 0.8rem 1rem;
            border-radius: 0 18px 18px 0;
            margin-top: 0.8rem;
        }
        @media (max-width: 900px) {
            .body-stage {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    organ_meta = _get_organ_metadata(selected_organ, system)
    system_color = SYSTEM_COLORS.get(system, "#8b5cf6")

    st.markdown(
        f"""
        <div class='holo-body-panel'>
          <div class='body-stage'>
            <div>{_render_organ_svg(system, selected_organ, view_mode)}</div>
            <div class='data-card'>
              <div class='section-pill'>{system}</div>
              <h3 style='margin: 0 0 0.35rem 0; color: #F8FAFC;'>{selected_organ}</h3>
              <div class='atlas-inline-metrics'>
                <span class='atlas-chip'>System: {system}</span>
                <span class='atlas-chip'>View: {view_mode}</span>
              </div>
              <div style='color: {system_color}; font-weight: 600; margin-bottom: 0.6rem;'>Mission relevance</div>
              <p style='color: #E2E8F0; margin: 0 0 0.8rem 0;'>{organ_meta['astronaut_context']}</p>
              <div style='font-size: 0.8rem; color: #A5F3FC; margin-bottom: 0.2rem;'>Function</div>
              <p style='color: #E2E8F0; margin: 0 0 0.8rem 0;'>{organ_meta['function']}</p>
              <div style='font-size: 0.8rem; color: #A5F3FC; margin-bottom: 0.2rem;'>Scientific note</div>
              <p style='color: #E2E8F0; margin: 0;'>{organ_meta['description']}</p>
              <div class='mission-story'>
                <strong style='color: #F8FAFC;'>Mission story</strong>
                <p style='color: #DDE7F3; margin: 0.35rem 0 0; font-size: 0.88rem;'>{_system_description(system)}</p>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    session = SessionLocal()
    try:
        direct_indicators: list[dict[str, Any]] = []
        for metric in SYSTEMS[system]["metrics"]:
            row = get_measurements_for_metric(session, metric)
            if row:
                latest = row[-1]
                direct_indicators.append({
                    "label": metric.replace("_", " ").title(),
                    "value": latest.value,
                    "unit": latest.unit,
                    "timestamp": latest.timestamp.strftime("%Y-%m-%d %H:%M"),
                })

        coverage = round((len(direct_indicators) / max(1, len(SYSTEMS[system]["metrics"])) * 100)) if SYSTEMS[system]["metrics"] else 0
        posture = "Nominal" if coverage >= 75 else "Watchlist" if coverage >= 40 else "Limited"

        summary_cols = st.columns(3)
        with summary_cols[0]:
            st.metric("Signal coverage", f"{coverage}%")
        with summary_cols[1]:
            st.metric("Mission posture", posture)
        with summary_cols[2]:
            st.metric("Focus structure", selected_organ)

        tabs = st.tabs(["Mission metrics", "System interpretation", "Educational resources"])

        with tabs[0]:
            if direct_indicators:
                for item in direct_indicators:
                    st.metric(label=item["label"], value=f"{item['value']} {item['unit']}", delta=item["timestamp"])
            else:
                st.info("No direct measurements are currently associated with this system.")

        with tabs[1]:
            st.info(_system_description(system))
            metric = SYSTEMS[system]["metrics"][0]
            rows = get_measurements_for_metric(session, metric)
            if rows:
                df = pd.DataFrame({"timestamp": [row.timestamp for row in rows], "value": [row.value for row in rows]})
                fig = px.line(df, x="timestamp", y="value", markers=True, color_discrete_sequence=[system_color])
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=8, r=8, t=8, b=8),
                    font=dict(color="#F4F3FF"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("No trend data is available for this system yet.")

        with tabs[2]:
            for item in organ_meta["resources"]:
                st.markdown(f"- {item}")
            st.write(organ_meta["description"])
    finally:
        session.close()
