from pathlib import Path
from typing import Any, cast
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import json
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.lineplots import LinePlot
from config.settings import ROOT_DIR
from database.database import SessionLocal
from database.models import AstronautProfile
from database.repository import ensure_astronaut, save_scientific_report
from database.measurements import measurement_frame
from intelligence.engine import analyze


def generate_pdf_report(session=None, output_path=None, astronaut_id=None, start=None, end=None):
    should_close = session is None
    session = session or SessionLocal()
    try:
        astronaut = ensure_astronaut(session) if astronaut_id is None else session.get(AstronautProfile, astronaut_id)
        if astronaut is None:
            raise ValueError("Unknown astronaut")
        analysis = analyze(session, astronaut.id, start, end)
        frame = measurement_frame(session, astronaut.id, start=start, end=end)
        output_path = Path(output_path) if output_path else ROOT_DIR / "data/processed" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") / "theia_report.pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        story: list[Any] = []
        def paragraph(text, style="BodyText"):
            story.append(Paragraph(escape(str(text)), styles[style]))
            story.append(Spacer(1, 6))
        paragraph("THEIA Mission Health Report", "Title")
        paragraph(f"Astronaut: {astronaut.name} | Mission: {astronaut.mission_id}")
        paragraph(f"Period (UTC): {analysis['period'].get('first', 'no observations')} to {analysis['period'].get('last', 'no observations')}")
        paragraph(f"Snapshot: {analysis['fingerprint']}")
        paragraph(f"Data quality: {analysis['quality']['total']} records; {analysis['quality']['excluded']} excluded.")
        paragraph(f"Recorded provenance: {analysis['quality']['sources']}")
        paragraph("Action plan", "Heading2")
        paragraph("Review source labels, incomplete observations and statistical flags with qualified mission staff. No individual medical treatment is inferred.")
        if not analysis["metrics"]:
            paragraph("Insufficient valid data for personal baseline or anomaly analysis.")
        for key, item in analysis["metrics"].items():
            paragraph(f"{item['metric']} | {item['cohort']} | {item['unit']}", "Heading2")
            paragraph(f"Samples: {item['samples']} | Status: {item['status']} | Latest: {item['latest']:.3f} {item['unit']} at {item['latest_timestamp']} UTC")
            paragraph(f"Mean: {item['mean']:.3f} | Median: {item['median']:.3f} | Standard deviation: {item['std']:.3f}")
            slope = f"{item['slope_per_day']:.4f}" if item['slope_per_day'] is not None else "insufficient data"
            change = f"{item['recent_change']:.3f}" if item['recent_change'] is not None else "no previous observation"
            paragraph(f"Trend per day: {slope} | Change vs previous: {change}")
            paragraph(f"Sources: {item['sources']} | Statistical flags: {len(item['anomalies'])}")
            paragraph(item['explanation'])
            rows = frame[(frame.metric_name == item['metric']) & frame.source.isin(item['sources']) & (frame.data_quality_status == 'VALID')]
            if len(rows) >= 2:
                drawing = Drawing(450, 150)
                chart = cast(Any, LinePlot()); chart.x = 40; chart.y = 25; chart.width = 395; chart.height = 110
                origin = rows.timestamp.min()
                points = [((row.timestamp - origin).total_seconds()/86400, float(row.value)) for row in rows.itertuples()]
                chart.data = [points]; chart.lines[0].strokeColor = colors.HexColor('#087f8c')
                chart.xValueAxis.valueMin = 0
                chart.xValueAxis.valueMax = max(points[-1][0], 1)
                chart.yValueAxis.labels.fontSize = 7; chart.xValueAxis.labels.fontSize = 7
                drawing.add(chart); drawing.add(String(45, 4, "Days since first observation (UTC)", fontSize=8))
                story.append(drawing)
            for flag in item['anomalies']:
                paragraph(f"Flag ID {flag['id']}: {flag['timestamp']} | {flag['value']} {item['unit']} | z={flag['z_score']:.3f} | {', '.join(flag['methods'])}")
        paragraph("Exploratory relationships", "Heading2")
        if not analysis['relationships']:
            paragraph("Insufficient paired days for correlations.")
        for relation in analysis['relationships']:
            paragraph(str(relation))
        paragraph("Limitations", "Heading2"); paragraph(analysis['limitations'])
        paragraph("References", "Heading2")
        paragraph("NASA Human Research Program: https://www.nasa.gov/hrp/")
        paragraph("NASA human physiology context: https://www.nasa.gov/missions/station/human-research-studying-astronaut-physiology/")
        paragraph("Isolation Forest implementation: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html")
        def footer(canvas, doc):
            canvas.setFont("Helvetica", 8); canvas.drawString(42, 25, f"THEIA experimental analytics | Page {doc.page}")
        SimpleDocTemplate(str(output_path), pagesize=letter, rightMargin=42, leftMargin=42, topMargin=36, bottomMargin=40, pageCompression=0).build(story, onFirstPage=footer, onLaterPages=footer)
        save_scientific_report(session, "mission_health_pdf", f"THEIA Mission Health Report - {astronaut.name}", json.dumps({"fingerprint": analysis['fingerprint'], "astronaut_id": astronaut.id}), str(output_path), "NASA HRP; THEIA local measurements; scikit-learn Isolation Forest")
        return output_path
    finally:
        if should_close:
            session.close()


def render_reports():
    with SessionLocal() as session:
        profile_id = ensure_astronaut(session).id
    if st.session_state.get('report_profile_id') != profile_id:
        st.session_state.pop('report_bytes', None)
    st.caption("Mission Reports workspace")
    st.caption("PDF uses the same versioned statistical snapshot as Dashboard, Intelligence Center and anatomy panels.")
    if st.button("Generate PDF report", key="generate_report"):
        path = generate_pdf_report()
        st.session_state['report_bytes'] = path.read_bytes()
        st.session_state['report_profile_id'] = profile_id
        st.success("Report generated and registered locally.")
    if 'report_bytes' in st.session_state:
        st.download_button("Download report", st.session_state['report_bytes'], "theia_report.pdf", "application/pdf")
