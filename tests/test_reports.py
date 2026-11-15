from __future__ import annotations

from database.database import SessionLocal, init_db
from database.repository import get_report_documents, save_health_measurement, seed_sample_data
from modules.reports.reports import generate_pdf_report


def test_generate_pdf_report_records_a_scientific_report():
    init_db()
    session = SessionLocal()
    try:
        seed_sample_data(session)
        report_path = generate_pdf_report(session=session)

        assert report_path.exists()
        documents = get_report_documents(session)
        assert any(doc.title.startswith("THEIA") for doc in documents)
        assert any(doc.file_path and "theia_report.pdf" in doc.file_path for doc in documents)

        pdf_text = report_path.read_text(encoding="utf-8", errors="ignore")
        assert "Action plan" in pdf_text or "Mission actions" in pdf_text
    finally:
        session.close()


def test_save_health_measurement_persists_real_metric_input():
    init_db()
    session = SessionLocal()
    try:
        seed_sample_data(session)
        saved = save_health_measurement(
            session,
            metric_name="sleep_hours",
            value=7.4,
            unit="hours",
            source="MANUAL_INPUT",
            mission_context="Evening check-in",
            notes="Rest quality was slightly below goal.",
        )

        assert saved.metric_name == "sleep_hours"
        assert saved.value == 7.4
        assert saved.source == "MANUAL_INPUT"
    finally:
        session.close()
