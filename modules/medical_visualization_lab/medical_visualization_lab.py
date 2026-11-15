import os
import streamlit as st
import requests
from modules.ui.theme import apply_theia_theme, render_page_header

OHIF_BASE_URL = os.environ.get("THEIA_OHIF_URL", "http://localhost:3001").rstrip("/")
OHIF_VIEWER_URL = OHIF_BASE_URL + "/local"


def viewer_status():
    try:
        response = requests.get(OHIF_BASE_URL + '/app-config.js', timeout=2)
        return response.ok and "Local files only" in response.text
    except requests.RequestException:
        return False


def render_medical_visualization_lab():
    apply_theia_theme()
    render_page_header("Medical Visualization Lab", "OHIF | Local DICOM review")
    if not viewer_status():
        st.warning("Local OHIF is unavailable or is using a different configuration. Start scripts/start_theia_services.py to serve the local-only viewer.")
        return
    st.success("Local viewer server responds with THEIA's local-only configuration.")
    st.info("No DICOM studies are bundled. Choose compatible local DICOM files in OHIF. This configuration has no external DICOMweb source; studies stay in the browser.")
    st.iframe(OHIF_VIEWER_URL, height=850)
    st.link_button("Open local DICOM viewer", OHIF_VIEWER_URL)
    st.caption("An HTTP response verifies the server, not diagnostic image compatibility. Study rendering requires a real compatible DICOM study.")
