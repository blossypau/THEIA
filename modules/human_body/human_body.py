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
    from modules.ui.theme import info_card, section_heading, navigation_button
    from services.ui_status import VISUAL_URL, service_snapshot
    from services.anatomy import structure_system
    from services.analysis_views import metric_view, history_figure
    apply_theia_theme()
    render_page_header("Human Body Explorer", "Educational anatomical atlas / not a personalized digital twin")
    registry = structure_registry()
    if not registry:
        st.warning("Anatomical model is missing. See the viewer setup in README.")
        return
    if '_anatomy_pending_sync' in st.session_state:
        st.session_state['anatomy_structure']=st.session_state.pop('_anatomy_pending_sync')
    def request_viewer_command():
        st.session_state['anatomy_command_revision']=st.session_state.get('anatomy_command_revision',0)+1
    def system_changed():
        request_viewer_command()
        selected=st.session_state.get('active_structure')
        system=st.session_state.get('anatomy_system','All')
        if selected and system!='All' and structure_system(selected)!=system:
            st.session_state['active_structure']=None
            st.session_state['anatomy_structure']=None
    controls = st.columns([1,2])
    with controls[0]:
        systems=sorted({structure_system(name) for name in registry})
        system_filter=st.selectbox('Model system',['All',*systems],key='anatomy_system',on_change=system_changed)
    with controls[1]:
        options=[name for name in registry if system_filter=='All' or structure_system(name)==system_filter]
        def choose_keyboard_structure():
            request_viewer_command()
            st.session_state['active_structure']=st.session_state.get('anatomy_structure')
        st.selectbox('Available model structure (keyboard alternative)',options,index=None,key='anatomy_structure',on_change=choose_keyboard_structure)
    def step_structure(direction):
        request_viewer_command()
        current=st.session_state.get('active_structure')
        position=options.index(current) if current in options else (0 if direction<0 else -1)
        identifier=options[(position+direction)%len(options)]
        st.session_state['active_structure']=identifier
        st.session_state['anatomy_structure']=identifier
    with st.container(horizontal=True):
        st.button('Previous structure',key='anatomy_previous',on_click=step_structure,args=(-1,),disabled=not options,icon=':material/chevron_left:')
        st.button('Next structure',key='anatomy_next',on_click=step_structure,args=(1,),disabled=not options,icon=':material/chevron_right:')
    st.caption(f'{len(options)} available structures in this group. Groups are educational, inferred from model labels; no additional anatomy is synthesized.')
    with st.container(key='anatomy_stage'):
        overview,viewer,signals=st.columns([1,2.5,1.3],gap='medium')
        with viewer:
            if service_snapshot()['Anatomy / 3D']:
                selection=anatomy_selection_component(key='anatomy_picker',viewer_url=VISUAL_URL+'/',selected_identifier=st.session_state.get('active_structure'),visible_identifiers=options,command_revision=st.session_state.get('anatomy_command_revision',0))
            else:
                selection=None
                st.warning('Local 3D service is unavailable. Start scripts/start_theia_services.py; the keyboard selector still loads analysis panels.')
        if isinstance(selection,dict) and selection.get('timestamp')!=st.session_state.get('last_anatomy_event'):
            st.session_state['last_anatomy_event']=selection.get('timestamp')
            st.session_state['active_structure']=selection.get('identifier') if selection.get('action')!='selection-cleared' else None
            selected=st.session_state['active_structure']
            if selected not in registry:selected=None
            if st.session_state.get('anatomy_structure')!=selected:
                st.session_state['_anatomy_pending_sync']=selected
                st.rerun()
        identifier=st.session_state.get('active_structure')
        if identifier and identifier not in registry:
            st.warning('The selection does not match this model version.');identifier=None
        with SessionLocal() as session:
            astronaut=ensure_astronaut(session)
            with overview:
                section_heading('Anatomy console','MODEL INVENTORY')
                info_card('AVAILABLE STRUCTURES',len(registry),'Real mesh nodes from the local GLB')
                info_card('ACTIVE ASTRONAUT',astronaut.name,astronaut.mission_id,'violet')
                st.caption('Drag to rotate. Scroll to zoom. Select a structure to connect it with personal history. Isolate, change opacity, or switch to wireframe in the viewer.')
                navigation_button('Review health analytics','Health Dashboard','anatomy_to_health',':material/monitoring:')
            with signals:
                section_heading('Linked signals','SHARED ANALYTICS')
                if not identifier:
                    info_card('SELECTION','Awaiting input','Click an actual structure or use the keyboard selector.')
                else:
                    view=anatomy_view(session,astronaut.id,identifier)
                    st.subheader(identifier)
                    st.caption(f"Real mesh ID: {identifier} | System: {view['system']}")
                    metadata=view['metadata']
                    detail=metadata.get('nameDetail') or metadata.get('description')
                    if detail:st.write(detail)
                    else:st.caption('The GLB supplies the structure identifier but no detailed functional description for this node. The system note below provides general educational context.')
                    for metric in view['metrics']:
                        metric_data=metric_view(session,astronaut.id,metric)
                        st.caption(metric.replace('_',' ').upper())
                        if metric_data['history'].empty:
                            st.info('No recorded measurements.')
                        else:
                            last=metric_data['history'].iloc[-1]
                            st.metric(metric.replace('_',' ').title(),f'{last.value:g} {last.unit}')
                            figure=history_figure(metric_data);figure.update_layout(height=210,showlegend=False,margin=dict(l=8,r=8,t=15,b=12))
                            st.plotly_chart(figure,key=f'anatomy_signal_{metric}',width='stretch')
                            for baseline in metric_data['baselines']:
                                st.caption(f"{baseline['cohort']} · retrospective period mean {baseline['mean']:.2f} ± {baseline['std']:.2f} {baseline['unit']} · {len(baseline['anomalies'])} statistical flags; not an independent baseline")
                    if not view['metrics']:st.info('No relevant direct physiological indicators configured.')
            if identifier:
                st.info(CONTEXT[structure_system(identifier)])
                st.caption('Altered gravity is educational context for bone and muscle research. This atlas does not detect bone loss, atrophy, fluid shifts or balance impairment.')
                st.link_button('NASA: gravity fields and human adaptation','https://www.nasa.gov/hrp/hazard-gravity-fields/')
            with st.expander('Model attribution and scientific context'):
                st.caption('Z-Anatomy model adapted by hpfrei; CC BY-SA 4.0. THEIA holographic rendering and integration adaptations use the same license. The model is anatomical; source colors and opacity are visualization choices, not findings.')
                st.link_button('NASA human research context','https://www.nasa.gov/hrp/')
                st.caption('openAnatomy is a desktop camera/MediaPipe hand overlay; it supplies no compatible web atlas here.')
