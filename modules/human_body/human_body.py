import streamlit as st
from components.anatomy_selection import anatomy_selection_component
from database.database import SessionLocal
from database.repository import ensure_astronaut
from services.anatomy import structure_registry, anatomy_view
from services.analysis_views import render_analysis
from modules.ui.theme import apply_theia_theme, render_page_header

CONTEXT = {
 "Musculoskeletal": "Microgravity reduces skeletal loading. Fatigue and sleep are contextual self-reports, not measurements of bone density or muscle loss.",
 "Cardiovascular": "Fluid redistribution and altered gravitational loading are relevant to cardiovascular adaptation. These measurements alone cannot assess structural heart health.",
 "Respiratory": "Oxygen saturation provides physiological context and does not establish a structural lung finding.",
 "Nervous": "Sleep and fatigue provide performance context, not a diagnosis of a selected neural structure.",
 "Digestive": "Glucose provides metabolic context, not direct organ function assessment.",
 "Urinary": "No direct renal or urinary measurements are configured."
}


def render_human_body():
    apply_theia_theme()
    render_page_header("Human Body Explorer", "Real GLB structures | Session-specific selection | Shared mission analytics")
    registry = structure_registry()
    if not registry:
        st.warning("Anatomical model is missing. See the external viewer setup in README.")
        return
    st.caption("Z-Anatomy model adapted by hpfrei; CC BY-SA 4.0. THEIA integration modifications are provided under the same license. Rotate by dragging, scroll to zoom, click to select; click again to reveal deeper layers. Reset restores the view.")
    selection = anatomy_selection_component(key="anatomy_picker")
    st.caption("The 3D viewer must be served locally on port 3002. Only structures contained in this model can be selected.")
    from services.anatomy import structure_system
    systems = sorted({structure_system(name) for name in registry})
    system_filter = st.selectbox("Model system", ["All", *systems], key="anatomy_system")
    options = [name for name in registry if system_filter == "All" or structure_system(name) == system_filter]
    def choose_keyboard_structure():
        st.session_state['active_structure'] = st.session_state.get('anatomy_structure')
    fallback = st.selectbox("Available model structure (keyboard alternative)", options, index=None, key="anatomy_structure", on_change=choose_keyboard_structure)
    if isinstance(selection, dict) and selection.get('timestamp') != st.session_state.get('last_anatomy_event'):
        st.session_state['last_anatomy_event'] = selection.get('timestamp')
        st.session_state['active_structure'] = selection.get('identifier') if selection.get('action') != 'selection-cleared' else None
    identifier = st.session_state.get('active_structure')
    if not identifier:
        st.info("Select a real structure in the model or in the list to load its data panels.")
        return
    if identifier not in registry:
        st.warning("The viewer selection does not match this model version.")
        return
    with SessionLocal() as session:
        astronaut = ensure_astronaut(session)
        view = anatomy_view(session, astronaut.id, identifier)
        st.subheader(identifier.replace('_', ' '))
        st.caption(f"Real mesh ID: {identifier} | System: {view['system']}")
        st.info(CONTEXT[view["system"]])
        for metric in view["metrics"]:
            st.subheader(metric.replace('_', ' '))
            render_analysis(session, astronaut.id, metric, f"anatomy_{metric}")
        if not view["metrics"]:
            st.info("No relevant direct physiological indicators configured.")
        st.link_button("NASA human research context", "https://www.nasa.gov/hrp/")
    st.caption("The downloaded openAnatomy project is a desktop camera/MediaPipe hand overlay, not a web anatomical atlas. No compatible licensed 3D assets were found there.")
