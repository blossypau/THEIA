import streamlit as st
import plotly.express as px
import pandas as pd
from pathlib import Path
from database.database import SessionLocal
from database.repository import seed_nasa_studies, get_imported_datasets
from services.datasets import register_table
from modules.ui.theme import apply_theia_theme, render_page_header, info_card, section_heading

VERIFIED_STUDY = {"id": "OSD-569", "title": "Inspiration4 whole-blood research", "url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-569", "reference": "https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/"}


def render_nasa_data_hub():
    from config.web import public_demo
    apply_theia_theme()
    render_page_header("NASA Data Hub", "Curated evidence catalogue | Local research tables | No live scientific feed")
    st.caption("Catalogue entries describe research topics; local HRP-* identifiers are THEIA catalogue keys, not NASA dataset accessions.")
    with st.expander('GeneLab processing context - methods, not astronaut biomarkers'):
        st.write('GeneLab standardizes assay-specific processing of spaceflight omics. THEIA has no FASTQ, expression matrix or methylation reads; these pipelines are not run against scalar mission measurements.')
        st.link_button('Pinned GeneLab processing methods','https://github.com/nasa/GeneLab_Data_Processing/tree/6d0c0fa9ffe2453a66334dcfd274fa2f726ab540')
        st.caption('Pipeline licensing is assay-specific (NOSA 1.3 and a Microarray GPL variant), with additional third-party conditions. Public sample metadata below provides experimental context, not individual risk or gene-expression results.')
    with st.expander('Reproducible NASA POWER environmental reference',expanded=False):
        from services.nasa_power import load_reference,fetch_power
        reference,metadata=load_reference()
        st.caption('PUBLIC RESEARCH: seven days of real NASA/MERRA2 gridded Earth weather near Kennedy Space Center in January 2024. Not spacecraft cabin or astronaut physiology.')
        st.json(metadata)
        st.dataframe(reference,hide_index=True)
        parameter=st.selectbox('NASA reference variable',reference.metric.unique(),key='power_variable')
        selected=reference[reference.metric==parameter].copy();selected['timestamp']=pd.to_datetime(selected.timestamp)
        st.line_chart(selected,x='timestamp',y='value',y_label=selected.unit.iloc[0],alt='Historical NASA POWER terrestrial environmental reference')
        st.download_button('Download reproducible NASA reference CSV',reference.to_csv(index=False),'nasa-power-earth-reference.csv','text/csv')
        if st.button('Fetch same NASA POWER period and register research table',key='fetch_power',disabled=public_demo()):
            import requests
            try:
                with SessionLocal() as research_session:record,frame=fetch_power(research_session)
                st.success(f'{record.row_count} quantitative public observations registered separately from astronaut records.')
            except (ValueError,requests.RequestException,KeyError) as exc:st.error(str(exc))
    term = st.text_input("Search catalogue", key="nasa_search").lower()
    with SessionLocal() as session:
        studies = seed_nasa_studies(session)
        organism = st.selectbox("Organism", ["All", *sorted({s.organism for s in studies})], key="nasa_organism")
        filtered=[study for study in studies if term in f"{study.title} {study.variables} {study.notes}".lower() and (organism=='All' or study.organism==organism)]
        section_heading('Research evidence library',f'{len(filtered)} CURATED TOPICS')
        if not filtered:st.info('No topics match these filters.')
        columns=st.columns(2)
        for index,study in enumerate(filtered):
            with columns[index%2]:
                with st.container(border=True):
                    st.caption(('HUMAN RESEARCH CONTEXT' if study.is_human else 'PRECLINICAL RESEARCH CONTEXT')+' / CURATED TOPIC')
                    st.subheader(study.title)
                    st.write(study.notes)
                    st.caption(f"{study.organism} · THEIA catalogue key {study.study_id}")
                    st.link_button('Explore official source',study.source_url,key=f'source_{study.id}',icon=':material/open_in_new:')
        st.divider()
        section_heading("Human spaceflight research", "VERIFIED ACCESSION / OSD-569")
        st.write(VERIFIED_STUDY['title'])
        st.link_button("OSD-569 repository", VERIFIED_STUDY['url'])
        st.link_button("NASA source identifying this dataset", VERIFIED_STUDY['reference'])
        st.caption("Public omics research is not direct crew telemetry. Access and reuse terms must be reviewed at the source. No human subject files are downloaded automatically.")
        section_heading("Preclinical sample explorer", "PUBLIC NASA API / OSD-1")
        st.caption("Drosophila spaceflight immunology research (preclinical). This imports real sample characteristics and experimental factors, not human physiological measurements or gene expression values.")
        if st.button("Fetch NASA OSD-1 sample metadata", key="fetch_osdr",disabled=public_demo()):
            from services.datasets import fetch_osdr_sample_table
            import requests
            try:
                record, _, title = fetch_osdr_sample_table(session)
                st.success(f"{title}: {record.row_count} public sample records registered locally.")
            except (requests.RequestException, ValueError, KeyError) as exc:
                session.rollback(); st.error(f"NASA public metadata unavailable: {exc}")
        uploaded = st.file_uploader("Import scientific CSV/TSV", type=["csv", "tsv"], key="nasa_csv_upload",disabled=public_demo())
        source_url = st.text_input("Dataset source URL or local provenance", value="USER_IMPORT", key="dataset_source")
        if uploaded and st.button("Validate and register research table", key="register_dataset"):
            try:
                record, frame = register_table(session, uploaded.getvalue(), uploaded.name, source_url)
                st.success(f"Registered {record.row_count} rows; repeated uploads reuse the same record.")
            except (ValueError, OSError) as exc:
                session.rollback(); st.error(f"Could not import table: {exc}")
        datasets = get_imported_datasets(session)
        if not datasets:
            st.info("No local research datasets registered.")
            return
        selected = st.selectbox("Registered research dataset", datasets, format_func=lambda r: f"{r.id}: {r.file_name} ({r.row_count} rows)", key="research_table")
        st.caption(selected.notes or selected.source_label)
        try:
            frame = pd.read_csv(selected.file_path)
        except (OSError, ValueError) as exc:
            st.error(f"Registered file unavailable: {exc}"); return
        st.dataframe(frame.head(1000))
        st.dataframe(frame.describe(include="all").T)
        st.write("Missing values", frame.isna().sum().to_dict())
        numeric = frame.select_dtypes(include="number").columns.tolist()
        if numeric:
            metric = st.selectbox("Scientific variable", numeric, key="research_variable")
            st.plotly_chart(px.histogram(frame, x=metric, template="plotly_dark"), key="research_histogram")
        categorical = [column for column in frame.columns if 1 < frame[column].nunique() <= 30 and column not in numeric]
        if categorical:
            category = st.selectbox("Sample characteristic", categorical, key="sample_category")
            counts = frame[category].value_counts().rename_axis(category).reset_index(name="samples")
            st.plotly_chart(px.bar(counts, x=category, y="samples", template="plotly_dark"), key="sample_counts")
        st.caption("Use Data Management to explicitly validate and import compatible measurement CSVs into the active mission profile. Research tables remain separate.")
