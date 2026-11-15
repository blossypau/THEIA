from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import DB_PATH


class Base(DeclarativeBase):
    pass


engine = create_engine(f"sqlite:///{DB_PATH}", future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from database.models import (
        AnomalyRecord,
        AstronautProfile,
        DailyCheckin,
        ExerciseRecord,
        GuidanceEntry,
        HealthMeasurement,
        MissionContext,
        MissionEvent,
        ModelAnalysisRecord,
        NutritionRecord,
        SensorMetadata,
    )

    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
