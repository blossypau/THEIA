"""Plain-text provenance badges are visible independently of color on every page."""
import json
import streamlit as st
from services.provenance import profile_provenance,summary,BOUNDARY


def render_provenance(session,astronaut_id):
    counts=summary(session,astronaut_id)
    st.caption('PROVENANCE / '+(' | '.join(f'{kind}: {count}' for kind,count in sorted(counts.items())) or 'NO DATA / NO VERIFIED SOURCE'))
    panel=st.expander('Data provenance and evidence',on_change='rerun')
    if panel.open:
      with panel:
        records=profile_provenance(session,astronaut_id)
        st.caption(BOUNDARY)
        st.caption('Declared source is retained separately. Legacy records without a 5.1 envelope are UNKNOWN_UNVERIFIED; historical receipt time is not invented.')
        if records:
            st.dataframe([{k:v for k,v in r.items() if k not in {'provenance_evidence','revisions'}} for r in records],hide_index=True)
            st.download_button('Download profile provenance and revision evidence',json.dumps(records,default=str,indent=2),
                'theia-provenance.json','application/json',key=f'provenance_export_{astronaut_id}')
