import streamlit as st
import requests
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
    with st.expander('Public DICOM codec demonstration'):
        from services.public_dicom import sample_manifest, fetch_sample
        info=sample_manifest()
        st.caption(info['origin'])
        st.caption(info['license'])
        st.link_button('Sample provenance and permitted use',info['source_notice'])
        if st.button('Fetch verified public CT sample',key='public_dicom_fetch'):
            try:
                with st.spinner('Downloading and checking the pinned public sample...'):
                    st.session_state['public_dicom_sample']=fetch_sample()
                st.success('Public sample verified: file hash, deidentification header and decoded pixel hash.')
            except ImportError:
                st.error('Install requirements-science.txt to verify this public DICOM sample.')
            except (ValueError, OSError, requests.RequestException) as exc:
                st.error(f'Public test sample unavailable: {exc}')
        if 'public_dicom_sample' in st.session_state:
            st.download_button('Download public CT codec sample',st.session_state['public_dicom_sample'],'theia-public-gray-ct.dcm','application/dicom',key='public_dicom_download')
            st.caption('Download, then choose this file using OHIF Upload files below. One anonymized CT slice for viewer testing only; not a full diagnostic study and never linked to an astronaut.')
    st.iframe(status.viewer_url, height=850, alt="OHIF local DICOM viewer")
    st.link_button("Open local DICOM viewer", status.viewer_url)
    st.caption("HTTP readiness verifies the viewer installation, not diagnostic image compatibility. Study rendering requires a real compatible DICOM study.")
