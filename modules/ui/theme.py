from __future__ import annotations

import streamlit as st


def apply_theia_theme() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :root {
                --bg: #080B18;
                --bg-2: #10162A;
                --card: #151D35;
                --card-strong: #1D2742;
                --panel-border: rgba(196, 181, 253, 0.2);
                --violet: #9B7BFF;
                --lavender: #C4B5FD;
                --cyan: #55D6E8;
                --text: #F4F3FF;
                --muted: #929BB5;
                --success: #7EF0C1;
                --warning: #FFB86C;
                --danger: #FF7F7F;
                --shadow: 0 22px 60px rgba(10, 12, 20, 0.45);
            }

            html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
                background: radial-gradient(circle at top, rgba(155, 123, 255, 0.12), transparent 35%),
                            linear-gradient(180deg, var(--bg) 0%, #0B1221 100%);
                color: var(--text);
                font-family: 'Inter', sans-serif;
            }

            .stApp {
                background: radial-gradient(circle at top left, rgba(85, 214, 232, 0.09), transparent 24%),
                            radial-gradient(circle at top right, rgba(155, 123, 255, 0.12), transparent 30%),
                            linear-gradient(180deg, var(--bg) 0%, #0B1221 100%);
            }

            .block-container {
                padding-top: 1.25rem;
                padding-bottom: 2.5rem;
                max-width: 1500px;
            }

            [data-testid="stSidebar"] {
                background: rgba(9, 13, 22, 0.88);
                border-right: 1px solid var(--panel-border);
                backdrop-filter: blur(16px);
            }

            .stSidebar .stRadio > div {
                display: flex;
                flex-direction: column;
                gap: 0.45rem;
                margin-top: 0.5rem;
            }

            .stSidebar [data-baseweb="radio"] > label {
                border-radius: 12px;
                border: 1px solid transparent;
                padding: 0.65rem 0.8rem;
                background: rgba(255,255,255,0.01);
                color: var(--text);
                transition: all 0.2s ease;
            }

            .stSidebar [data-baseweb="radio"] > label:hover {
                border-color: rgba(155, 123, 255, 0.35);
                background: rgba(155, 123, 255, 0.08);
            }

            .stSidebar [data-baseweb="radio"] > label[data-checked="true"] {
                background: linear-gradient(135deg, rgba(155, 123, 255, 0.16), rgba(85,214,232,0.1));
                border-color: rgba(155, 123, 255, 0.45);
                box-shadow: inset 0 0 0 1px rgba(196,181,253,0.2);
            }

            .brand-shell {
                padding: 1rem 0.8rem 0.75rem;
                margin-bottom: 0.6rem;
                border-bottom: 1px solid rgba(196, 181, 253, 0.12);
            }

            .brand-mark {
                display: flex;
                align-items: center;
                gap: 0.8rem;
                margin-bottom: 0.6rem;
            }

            .brand-orbit {
                width: 38px;
                height: 38px;
                border-radius: 50%;
                display: grid;
                place-items: center;
                background: linear-gradient(135deg, rgba(155, 123, 255, 0.3), rgba(85, 214, 232, 0.18));
                border: 1px solid rgba(196, 181, 253, 0.4);
                box-shadow: 0 0 28px rgba(155, 123, 255, 0.35);
                color: var(--text);
                font-size: 1.2rem;
            }

            .brand-name {
                font-weight: 700;
                font-size: 1.2rem;
                letter-spacing: 0.15em;
                text-transform: uppercase;
            }

            .status-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                padding: 0.28rem 0.7rem;
                border-radius: 999px;
                font-size: 0.7rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                background: rgba(126, 240, 193, 0.08);
                color: var(--success);
                border: 1px solid rgba(126, 240, 193, 0.28);
            }

            .status-pill::before {
                content: "";
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: currentColor;
                box-shadow: 0 0 12px currentColor;
            }

            .profile-quadrant {
                background: linear-gradient(135deg, rgba(155,123,255,0.14), rgba(85,214,232,0.08));
                border: 1px solid rgba(196, 181, 253, 0.18);
                border-radius: 16px;
                padding: 0.8rem 0.9rem;
                margin: 0.9rem 0 1rem;
            }

            .profile-label {
                font-size: 0.7rem;
                color: var(--muted);
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 0.3rem;
            }

            .profile-name {
                font-size: 1rem;
                font-weight: 700;
            }

            .mini-meta {
                color: var(--muted);
                font-size: 0.72rem;
            }

            .mission-shell {
                background: linear-gradient(180deg, rgba(21,29,53,0.9), rgba(16,22,42,0.82));
                border: 1px solid var(--panel-border);
                border-radius: 22px;
                padding: 1.2rem 1.3rem 1rem;
                box-shadow: var(--shadow);
                margin-bottom: 1rem;
            }

            .section-tag {
                color: var(--lavender);
                font-size: 0.74rem;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                margin-bottom: 0.7rem;
            }

            .mission-title {
                font-size: clamp(1.8rem, 2.5vw, 2.8rem);
                font-weight: 800;
                margin: 0.2rem 0 0.7rem;
                letter-spacing: -0.04em;
            }

            .mission-subtitle {
                color: var(--muted);
                font-size: 0.92rem;
                margin-bottom: 0.7rem;
            }

            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
            }

            .metric-card {
                background: linear-gradient(180deg, rgba(21,29,53,0.9), rgba(11,18,33,0.92));
                border: 1px solid var(--panel-border);
                border-radius: 18px;
                box-shadow: var(--shadow);
                padding: 0.9rem 1rem 0.85rem;
                min-height: 155px;
            }

            .metric-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: var(--muted);
                font-size: 0.7rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.8rem;
            }

            .quality-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                background: rgba(126, 240, 193, 0.1);
                color: var(--success);
                border: 1px solid rgba(126, 240, 193, 0.25);
                border-radius: 999px;
                padding: 0.18rem 0.5rem;
                font-size: 0.62rem;
            }

            .quality-pill::before {
                content: "";
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: currentColor;
            }

            .metric-value {
                font-size: clamp(1.6rem, 2vw, 2.2rem);
                font-weight: 700;
                letter-spacing: -0.04em;
                margin-bottom: 0.4rem;
            }

            .metric-value span {
                font-size: 0.78rem;
                color: var(--muted);
                letter-spacing: 0.04em;
                margin-left: 0.4rem;
            }

            .metric-delta {
                font-size: 0.72rem;
                color: var(--lavender);
                margin-bottom: 0.38rem;
            }

            .metric-meta {
                color: var(--muted);
                font-size: 0.7rem;
                line-height: 1.4;
            }

            .panel {
                background: linear-gradient(180deg, rgba(21,29,53,0.9), rgba(11,18,33,0.92));
                border: 1px solid var(--panel-border);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                box-shadow: var(--shadow);
            }

            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 1rem;
            }

            .timeline-item {
                display: grid;
                grid-template-columns: 18px 1fr;
                gap: 0.75rem;
                align-items: start;
                margin-bottom: 0.9rem;
                padding-bottom: 0.7rem;
                border-bottom: 1px solid rgba(196, 181, 253, 0.08);
            }

            .timeline-mark {
                width: 14px;
                height: 14px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--violet), var(--cyan));
                box-shadow: 0 0 18px rgba(155, 123, 255, 0.7);
                margin-top: 0.35rem;
            }

            .timeline-content {
                display: flex;
                flex-direction: column;
                gap: 0.18rem;
            }

            .timeline-title {
                font-weight: 700;
                color: var(--text);
            }

            .timeline-subtitle {
                color: var(--muted);
                font-size: 0.78rem;
            }

            .body-shell {
                background: linear-gradient(180deg, rgba(21,29,53,0.8), rgba(10,17,28,0.9));
                border-radius: 22px;
                border: 1px solid var(--panel-border);
                padding: 1rem;
            }

            .system-option {
                padding: 0.7rem 0.9rem;
                border-radius: 12px;
                border: 1px solid rgba(196, 181, 253, 0.12);
                background: rgba(255,255,255,0.02);
                margin-bottom: 0.7rem;
                color: var(--text);
            }

            .chart-panel {
                background: rgba(9, 13, 22, 0.35);
                border-radius: 16px;
                border: 1px solid rgba(196, 181, 253, 0.12);
                padding: 0.5rem;
            }

            .stTabs [role="tablist"] {
                gap: 0.5rem;
                margin-bottom: 1rem;
            }

            .stTabs [role="tab"] {
                border-radius: 999px;
                padding: 0.55rem 0.95rem;
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(196, 181, 253, 0.12);
                color: var(--muted);
            }

            .stTabs [role="tab"][aria-selected="true"] {
                background: linear-gradient(135deg, rgba(155,123,255,0.18), rgba(85,214,232,0.08));
                border-color: rgba(155, 123, 255, 0.45);
                color: var(--text);
            }

            .stButton > button {
                border-radius: 12px;
                border: 1px solid rgba(155, 123, 255, 0.32);
                background: linear-gradient(135deg, rgba(155, 123, 255, 0.14), rgba(85, 214, 232, 0.05));
                color: var(--text);
                font-weight: 600;
            }

            .stButton > button:hover {
                border-color: rgba(85, 214, 232, 0.5);
            }

            .stDataFrame {
                background: rgba(9, 13, 22, 0.35);
            }

            .stMetric {
                border: 1px solid rgba(196, 181, 253, 0.15);
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.015);
                padding: 0.8rem 0.9rem;
            }

            .stAlert {
                border-radius: 12px;
                border: 1px solid rgba(196, 181, 253, 0.15);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, unit: str, source: str, timestamp: str | None = None, delta: str = "") -> None:
    time_text = f"<div class='metric-meta'>{timestamp}</div>" if timestamp else ""
    delta_text = f"<div class='metric-delta'>{delta}</div>" if delta else ""
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-header'>
                <span>{title}</span>
                <span class='quality-pill'>LIVE</span>
            </div>
            <div class='metric-value'>{value}<span>{unit}</span></div>
            {delta_text}
            <div class='metric-meta'>{source}</div>
            {time_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class='mission-shell'>
            <div class='section-tag'>THEIA / Mission control</div>
            <div class='mission-title'>{title}</div>
            <div class='mission-subtitle'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
