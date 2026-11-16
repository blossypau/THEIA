import streamlit as st
from database.database import SessionLocal
from database.repository import ensure_astronaut, get_report_documents
from intelligence.engine import analyze
from services.analysis_views import render_analysis
from utils.measurement_schema import ALLOWED_METRICS
from modules.ui.theme import apply_theia_theme, render_page_header


def render_intelligence_center():
    apply_theia_theme()
    render_page_header("THEIA Intelligence Center", "Shared statistical engine | Reproducible SQLite snapshots")
    from modules.ui.theme import navigation_button
    navigation_button('Open longitudinal, HRV and data standards tools','Scientific Analysis','open_science',':material/science:')
    with SessionLocal() as session:
        astronaut = ensure_astronaut(session)
        result = analyze(session, astronaut.id)
        from modules.ui.theme import info_card, section_heading
        import plotly.graph_objects as go
        import pandas as pd
        columns=st.columns(3)
        with columns[0]:info_card('INPUT OBSERVATIONS',result['quality']['total'],'Current profile / local SQLite')
        with columns[1]:info_card('ANALYTIC COHORTS',len(result['metrics']),'Sources remain distinguishable','violet')
        with columns[2]:info_card('EXCLUDED RECORDS',result['quality']['excluded'],'Validation and quality checks','amber')
        metric=st.selectbox('Analysis indicator',sorted(ALLOWED_METRICS),index=sorted(ALLOWED_METRICS).index('heart_rate'),key='intelligence_metric')
        trajectory,relations=st.columns([1.5,1])
        with trajectory:
            section_heading('Baseline & deviations','EXPERIMENTAL STATISTICS')
            render_analysis(session,astronaut.id,metric,'intelligence')
        with relations:
            section_heading('Signal relationships','PAIRED UTC DAYS')
            if result['relationships']:
                cohorts=sorted({r.get('source',r['cohort']) for r in result['relationships']})
                cohort=st.selectbox('Relationship cohort',cohorts,key='correlation_cohort')
                relationships=[r for r in result['relationships'] if r.get('source',r['cohort'])==cohort]
                names=sorted({r[k] for r in relationships for k in ['left','right']})
                matrix=pd.DataFrame(float('nan'),index=names,columns=names)
                for name in names:matrix.loc[name,name]=1
                for relation in relationships:
                    matrix.loc[relation['left'],relation['right']]=relation['pearson_r']
                    matrix.loc[relation['right'],relation['left']]=relation['pearson_r']
                figure=go.Figure(go.Heatmap(z=matrix.values,x=names,y=names,zmin=-1,zmax=1,colorscale=[[0,'#9c78ff'],[.5,'#0b1e30'],[1,'#45e0f5']],colorbar=dict(title='r'),hoverongaps=False))
                figure.update_layout(height=330,template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',margin=dict(l=15,r=15,t=15,b=15))
                st.plotly_chart(figure,key='relationships_heatmap',width='stretch')
                st.caption('Pearson r on daily means, exact sources kept separate. Missing cells lack sufficient paired days. Exploratory, not causal or adjusted for confounding; counts below are part of the interpretation.')
                with st.expander('Paired sample counts'):st.dataframe(relationships,hide_index=True)
            else:
                st.info('At least five paired UTC days with variable values are required. No relationship is inferred from unpaired data.')
        from modules.ui.explanations import render_explanations
        from modules.ui.explanations import render_historical
        render_historical(session,astronaut.id,metric)
        st.caption('The following persisted flags retain retrospective window methods for historical compatibility; their reference includes the observation.')
        render_explanations(session,astronaut.id,result,metric)
        with st.expander('Methods, quality and reproducibility'):
            st.json({'snapshot':result['fingerprint'],'quality':result['quality'],'period':result['period'],'parameters':result['parameters']})
            st.caption(result['limitations'])
        st.caption("No predictive clinical model is trained or validated by this workflow.")
        st.subheader("Report registry")
        for record in get_report_documents(session)[:5]:
            st.write(record.title, record.generated_at)

        if st.toggle("Open predictive research experiment", key="predictive_research"):
            from database.measurements import measurement_frame
            from analytics.predictive import build_demo_regression
            frame = measurement_frame(session, astronaut.id)
            frame = frame[(frame.data_quality_status == 'VALID') & frame.source.isin(['MANUAL_INPUT', 'MANUALLY_ENTERED_DATA', 'REAL_SENSOR_DATA'])].copy()
            if frame.empty:
                st.info("No validated mission observations for this experiment.")
            else:
                frame['day'] = frame.timestamp.dt.floor('D')
                daily = frame.pivot_table(index='day', columns='metric_name', values='value', aggfunc='mean')
                target = st.selectbox("Experimental target", daily.columns.tolist(), key="prediction_target")
                features = st.multiselect("Experimental predictors", [c for c in daily.columns if c != target], key="prediction_features")
                if st.button("Run educational regression", key="run_regression"):
                    st.json(build_demo_regression(daily, target, features))
                st.caption("Exploratory held-out random split, not a prospective time-series validation or a medical forecast.")
