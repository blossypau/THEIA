"""Short-lived HTTP service checks; never infer connectivity from saved measurements."""
import requests
import streamlit as st
from services.ohif_runtime import resolve_ohif

VISUAL_URL='http://127.0.0.1:3004'

@st.cache_data(ttl=5,show_spinner=False)
def service_snapshot():
    states={}
    for name,url,marker in [('Anatomy / 3D',VISUAL_URL+'/theia/visual-health','theia-visuals'),('Integration API','http://127.0.0.1:8765/health','theia-integration-api')]:
        try:
            response=requests.get(url,timeout=.6)
            states[name]=response.ok and response.json().get('service')==marker
        except (requests.RequestException,ValueError):states[name]=False
    states['OHIF']=resolve_ohif().ready
    return states
