from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from config.settings import ROOT_DIR
from database.database import SessionLocal
from database.repository import get_imported_datasets, save_imported_dataset, seed_nasa_studies, search_nasa_studies
from modules.ui.theme import apply_theia_theme, render_page_header


def _handle_csv_upload() -> None:
    uploaded = st.file_uploader("Import a compatible science CSV for local analysis", type=["csv", "tsv", "txt"], key="nasa_csv_upload")
    if uploaded is None:
        return

    target_dir = ROOT_DIR / "data" / "imports"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / uploaded.name
    with target_path.open("wb") as fh:
        fh.write(uploaded.getvalue())

    try:
        frame = pd.read_csv(target_path)
        row_count = int(len(frame))
        columns = ", ".join(frame.columns.tolist())
        session = SessionLocal()
        try:
            save_imported_dataset(
                session,
                study_id="USER-IMPORT",
                file_name=uploaded.name,
                file_path=str(target_path),
                columns=columns,
                row_count=row_count,
                notes="Imported from local NASA data review workflow.",
            )
        finally:
            session.close()
        st.success(f"Dataset captured with {row_count} rows and {len(frame.columns)} columns.")
    except Exception as exc:  # pragma: no cover - UI guard
        st.warning(f"The uploaded file could not be parsed as a table: {exc}")


def render_nasa_data_hub() -> None:
    apply_theia_theme()
    render_page_header("NASA Data Hub", "Official NASA evidence • reusable dataset catalog • science import workflow")

    session = SessionLocal()
    try:
        studies = seed_nasa_studies(session)
    finally:
        session.close()

    st.markdown(
        """
        <div style='margin-bottom: 1rem; padding: 1rem 1.2rem; border-radius: 18px; background: rgba(14, 23, 33, 0.75); border: 1px solid rgba(125,211,252,0.3);'>
            <strong style='color:#E2E8F0;'>NASA evidence layer</strong>
            <p style='color:#D9F8FF; margin: 0.4rem 0 0;'>This module catalogs official NASA resources, relevant human-spaceflight research areas, and importable datasets while keeping all operational data local-first.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        search_term = st.text_input("Search the NASA evidence catalogue", value="")
        organism_filter = st.selectbox("Organism", ["All", "Human", "Human and cellular", "Human and animal", "Cellular"], index=0)
        study_filter = st.selectbox("Study type", ["All", "Physiology", "Bone and muscle research", "Behavioral and sleep health", "Immunology", "Radiation risk"], index=0)

    filtered = studies
    if search_term:
        filtered = search_nasa_studies(SessionLocal(), keyword=search_term, organism=None if organism_filter == "All" else organism_filter, study_type=None if study_filter == "All" else study_filter)
    elif organism_filter != "All" or study_filter != "All":
        filtered = search_nasa_studies(SessionLocal(), keyword="", organism=None if organism_filter == "All" else organism_filter, study_type=None if study_filter == "All" else study_filter)

    if not filtered:
        st.info("No NASA studies match the selected filters. The registry remains available for additional source review.")

    for study in filtered:
        cols = st.columns([2.2, 1.1])
        with cols[0]:
            st.markdown(f"### {study.title}")
            st.caption(f"{study.source_name} • {study.study_type} • {study.organism}")
            st.write(study.notes or "Scientific metadata for mission health design review.")
            st.write(f"Variables: {study.variables}")
            st.write(f"Space factors: {study.space_factors}")
            st.markdown(f"Source: [{study.source_url}]({study.source_url})")
            if study.file_url:
                st.markdown(f"Data reference: [{study.file_url}]({study.file_url})")
            st.write(f"References: {study.references}")
        with cols[1]:
            st.metric("Study ID", study.study_id)
            st.metric("Human", "Yes" if study.is_human else "No")
            st.metric("Animal", "Yes" if study.is_animal else "No")
            st.metric("Cellular", "Yes" if study.is_cellular else "No")

    st.markdown("---")
    st.subheader("Dataset import and validation")
    _handle_csv_upload()

    imported = get_imported_datasets(SessionLocal())
    if imported:
        st.subheader("Imported dataset log")
        for item in imported[:10]:
            st.write(f"- {item.file_name} • {item.row_count} rows • {item.imported_at.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info("No dataset has been imported yet. Use the uploader to bring local scientific files into the local THEIA database.")

    st.caption("NASA data are catalogued, checked, and contextualized; they are not treated as a medical diagnosis by default.")
