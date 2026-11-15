import streamlit as st
import plotly.express as px
import pandas as pd
from pathlib import Path
from database.database import SessionLocal
from database.repository import seed_nasa_studies, get_imported_datasets
from services.datasets import register_table
from modules.ui.theme import apply_theia_theme, render_page_header

VERIFIED_STUDY = {"id": "OSD-569", "title": "Inspiration4 whole-blood research", "url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-569", "reference": "https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/"}


def render_nasa_data_hub():
    apply_theia_theme()
    render_page_header("NASA Data Hub", "Curated evidence catalogue | Local research tables | No live scientific feed")
    st.caption("Catalogue entries describe research topics; local HRP-* identifiers are THEIA catalogue keys, not NASA dataset accessions.")
    term = st.text_input("Search catalogue", key="nasa_search").lower()
    with SessionLocal() as session:
        studies = seed_nasa_studies(session)
        organism = st.selectbox("Organism", ["All", *sorted({s.organism for s in studies})], key="nasa_organism")
        for study in studies:
            if term not in f"{study.title} {study.variables} {study.notes}".lower() or (organism != "All" and study.organism != organism):
                continue
            with st.expander(study.title):
                st.write(study.notes)
                st.caption(f"THEIA catalogue key: {study.study_id} | {study.organism}")
                st.link_button("Official research context", study.source_url, key=f"source_{study.id}")
        st.subheader("Verified public study")
        st.write(VERIFIED_STUDY['title'])
        st.link_button("OSD-569 repository", VERIFIED_STUDY['url'])
        st.link_button("NASA source identifying this dataset", VERIFIED_STUDY['reference'])
        st.caption("Public omics research is not direct crew telemetry. Access and reuse terms must be reviewed at the source. No human subject files are downloaded automatically.")
        st.subheader("Public NASA sample metadata - OSD-1")
        st.caption("Drosophila spaceflight immunology research (preclinical). This imports real sample characteristics and experimental factors, not human physiological measurements or gene expression values.")
        if st.button("Fetch NASA OSD-1 sample metadata", key="fetch_osdr"):
            from services.datasets import fetch_osdr_sample_table
            import requests
            try:
                record, _, title = fetch_osdr_sample_table(session)
                st.success(f"{title}: {record.row_count} public sample records registered locally.")
            except (requests.RequestException, ValueError, KeyError) as exc:
                session.rollback(); st.error(f"NASA public metadata unavailable: {exc}")
        uploaded = st.file_uploader("Import scientific CSV/TSV", type=["csv", "tsv"], key="nasa_csv_upload")
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
