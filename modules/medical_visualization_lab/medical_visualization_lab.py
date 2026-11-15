import streamlit as st
from modules.ui.theme import apply_theia_theme, render_page_header
from services.ohif_runtime import resolve_ohif


def viewer_status():
    return resolve_ohif().ready


def render_medical_visualization_lab():
    apply_theia_theme()
    render_page_header("Medical Visualization Lab", "OHIF | Local DICOM review")
    status = resolve_ohif()
    st.button("Recheck OHIF", key="recheck_ohif")
    if not status.ready:
        st.warning(f"OHIF is not ready at {status.base_url}. {status.reason}")
        st.code('.venv\\Scripts\\python.exe scripts\\start_theia_services.py --ohif-only', language='powershell')
        st.caption("The launcher preserves incompatible listeners and uses a free port automatically. Keep its terminal open, then click Recheck OHIF. If THEIA_OHIF_URL pins an old server, unset it to enable discovery.")
        return
    st.success("Local OHIF verified: server identity, configuration, /local route and JavaScript bundle.")
    st.caption(f"Active viewer: {status.viewer_url}")
    st.info("No DICOM studies are bundled. Choose compatible local DICOM files in OHIF. This configuration has no external DICOMweb source; studies stay in the browser.")
    st.iframe(status.viewer_url, height=850, alt="OHIF local DICOM viewer")
    st.link_button("Open local DICOM viewer", status.viewer_url)
    st.caption("HTTP readiness verifies the viewer installation, not diagnostic image compatibility. Study rendering requires a real compatible DICOM study.")
