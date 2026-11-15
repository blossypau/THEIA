from __future__ import annotations

import sqlite3
from contextvars import ContextVar
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect, text, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import DB_PATH


class Base(DeclarativeBase):
    pass


DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", future=True, echo=False, connect_args={"timeout": 30})

@event.listens_for(engine, "connect")
def sqlite_options(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
_main_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
session_factory_override = ContextVar('session_factory_override', default=None)

def SessionLocal(*args, **kwargs):
    factory = session_factory_override.get() or _main_factory
    return factory(*args, **kwargs)


def init_db() -> None:
    from database.models import (
        AnomalyRecord,
        AstronautProfile,
        DailyCheckin,
        ExerciseRecord,
        GuidanceEntry,
        HealthMeasurement,
        ImportedDataset,
        MissionContext,
        MissionEvent,
        ModelAnalysisRecord,
        NasaStudy,
        NutritionRecord,
        ScientificAnalysisRecord,
        ScientificReportDocument,
        SensorMetadata,
    )

    inspector = inspect(engine)
    if "health_measurements" in inspector.get_table_names() and "identity_key" not in {c["name"] for c in inspector.get_columns("health_measurements")}:
        backup_dir = DB_PATH.parent / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        with sqlite3.connect(DB_PATH) as source, sqlite3.connect(backup_dir / f"theia-before-v3-{stamp}.sqlite3") as backup:
            source.backup(backup)
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE health_measurements ADD COLUMN identity_key VARCHAR(64)"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_measurement_identity ON health_measurements(identity_key)"))
    Base.metadata.create_all(bind=engine)
    # Additive, versioned migration: existing measurements and report rows are retained.
    with engine.begin() as connection:
        connection.execute(text("INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES ('5.0-additive-context-provenance', CURRENT_TIMESTAMP)"))


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
