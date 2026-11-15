from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from config.settings import ROOT_DIR
from database.database import SessionLocal
from database.repository import get_dashboard_summary


def generate_pdf_report():
    output_path = ROOT_DIR / "data" / "processed" / "theia_report.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    session = SessionLocal()
    try:
        summary = get_dashboard_summary(session)
        measurements = summary["latest_measurements"]
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("THEIA Mission Health Report", styles['Title']))
        story.append(Paragraph(f"Mission ID: {summary['astronaut'].mission_id}", styles['Normal']))
        story.append(Paragraph(f"Astronaut: {summary['astronaut'].name}", styles['Normal']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Latest measurements", styles['Heading2']))
        for item in measurements:
            story.append(Paragraph(f"- {item.metric_name}: {item.value} {item.unit} on {item.timestamp}", styles['BodyText']))
        story.append(Spacer(1, 12))
        if summary["latest_checkin"]:
            story.append(Paragraph("Recent check-in summary", styles['Heading2']))
            c = summary["latest_checkin"]
            story.append(Paragraph(f"Sleep: {c.sleep_duration_hours}h | Mood: {c.mood}/100 | Energy: {c.energy}/100 | Fatigue: {c.fatigue}/100", styles['BodyText']))
        doc.build(story)
    finally:
        session.close()
    return output_path


def render_reports():
    st.subheader("Medical Reports")
    st.write("Generate a PDF review summary for authorized medical personnel.")
    if st.button("Generate PDF report"):
        report_path = generate_pdf_report()
        st.success(f"Report created at {report_path}")
    report_file = ROOT_DIR / "data" / "processed" / "theia_report.pdf"
    if report_file.exists():
        with report_file.open("rb") as file:
            st.download_button("Download report", file.read(), file_name="theia_report.pdf", mime="application/pdf")
