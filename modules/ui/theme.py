"""THEIA 4 visual primitives. Values are escaped; interactive controls stay native."""
from html import escape
from pathlib import Path
import streamlit as st

CSS = Path(__file__).with_name('command.css')


def apply_theia_theme():
    st.html('<style>' + CSS.read_text(encoding='utf-8') + '</style>')


def render_page_header(title, subtitle):
    st.markdown(f"<div class='page-heading'><div><div class='eyebrow'>THEIA / SPACE HEALTH COMMAND</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div><span class='outline-tag'>RESEARCH CONSOLE · 5.1</span></div>", unsafe_allow_html=True)


def section_heading(title, detail=''):
    st.markdown(f"<div class='section-heading'><h3>{escape(title)}</h3><span>{escape(detail)}</span></div>",unsafe_allow_html=True)


def render_metric_card(title, value, unit, source, timestamp=None, delta=''):
    st.markdown(f"<div class='signal-card'><span class='eyebrow'>{escape(title)}</span><div class='signal-value'>{escape(str(value))}<small>{escape(unit)}</small></div><p>{escape(delta)}</p><span class='data-label'>{escape(source)}</span><p>{escape(timestamp or '')}</p></div>",unsafe_allow_html=True)


def info_card(label, value, detail='', tone='cyan'):
    tone = tone if tone in {'cyan','violet','amber','green'} else 'cyan'
    st.markdown(f"<div class='readout {tone}'><div class='eyebrow'>{escape(label)}</div><div class='readout-value'>{escape(str(value))}</div><p>{escape(str(detail))}</p></div>",unsafe_allow_html=True)


def go_to(page):
    st.session_state['navigation'] = page


def navigation_button(label, page, key, icon=':material/arrow_forward:'):
    st.button(label, key=key, icon=icon, on_click=go_to, args=(page,), width='stretch')
