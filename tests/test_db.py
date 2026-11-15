from __future__ import annotations

import pandas as pd

from config.settings import ROOT_DIR
from database.database import SessionLocal, init_db
from database.models import HealthMeasurement
from database.repository import seed_sample_data
from intelligence.baseline_engine import compute_baseline
from integrations.csv_import import import_csv


def test_seed_data_creates_profile_and_measurements():
    init_db()
    session = SessionLocal()
    try:
        astronaut = seed_sample_data(session)
        assert astronaut.mission_id == "ARCTURUS-42"
        count = session.query(HealthMeasurement).filter_by(astronaut_id=astronaut.id).count()
        assert count > 0
    finally:
        session.close()


def test_baseline_works_on_measurements():
    values = pd.Series([62, 64, 63, 65, 66, 67])
    baseline = compute_baseline(values)
    assert baseline["samples"] == 6
    assert baseline["mean"] is not None
    assert baseline["confidence"] in {"moderate", "high"}


def test_csv_import_inserts_records():
    init_db()
    session = SessionLocal()
    try:
        astronaut = seed_sample_data(session)
        csv_path = ROOT_DIR / "data" / "sample" / "sample_health_data.csv"
        records = import_csv(session, str(csv_path), astronaut_id=astronaut.id)
        assert len(records) >= 1
        assert session.query(HealthMeasurement).filter_by(astronaut_id=astronaut.id).count() > 0
    finally:
        session.close()
