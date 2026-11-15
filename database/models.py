from __future__ import annotations

from utils.timestamps import utc_now

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class SchemaMigration(Base):
    __tablename__ = 'schema_migrations'
    version: Mapped[str] = mapped_column(String(50), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class MeasurementRevision(Base):
    __tablename__ = 'measurement_revisions'
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey('astronaut_profiles.id'), index=True)
    measurement_id: Mapped[int] = mapped_column(ForeignKey('health_measurements.id'), index=True)
    before_json: Mapped[str] = mapped_column(Text)
    after_json: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class MeasurementProvenance(Base):
    __tablename__ = 'measurement_provenance'
    measurement_id: Mapped[int] = mapped_column(ForeignKey('health_measurements.id'), primary_key=True)
    connector: Mapped[str] = mapped_column(String(100))
    instrument: Mapped[str] = mapped_column(String(200))
    receipt: Mapped[str] = mapped_column(String(100))
    capture_verified: Mapped[bool] = mapped_column(default=False)
    details: Mapped[str] = mapped_column(Text, default='{}')


class AcquisitionReceipt(Base):
    __tablename__ = 'acquisition_receipts'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey('astronaut_profiles.id'), index=True)
    connector: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    details: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ReportScope(Base):
    __tablename__ = 'report_scopes'
    report_id: Mapped[int] = mapped_column(ForeignKey('scientific_report_documents.id'), primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey('astronaut_profiles.id'), index=True)


class SpaceObservation(Base):
    """Typed mission context, kept separate from scalar physiology and never inferred from it."""
    __tablename__ = 'space_observations'
    id: Mapped[int] = mapped_column(primary_key=True)
    identity_key: Mapped[str] = mapped_column(String(64), unique=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey('astronaut_profiles.id'), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(50))
    quality: Mapped[str] = mapped_column(String(30))
    instrument: Mapped[str] = mapped_column(String(200))
    payload: Mapped[str] = mapped_column(Text)


class TestOutbox(Base):
    __test__ = False
    __tablename__ = 'test_outbox'
    id: Mapped[str] = mapped_column(ForeignKey('acquisition_receipts.id'), primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey('astronaut_profiles.id'), index=True)
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default='SYNC PENDING')


class AstronautProfile(Base):
    __tablename__ = "astronaut_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(100), nullable=False)
    mission_day: Mapped[int] = mapped_column(Integer, default=0)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    health_measurements: Mapped[list["HealthMeasurement"]] = relationship(back_populates="astronaut")
    checkins: Mapped[list["DailyCheckin"]] = relationship(back_populates="astronaut")
    contexts: Mapped[list["MissionContext"]] = relationship(back_populates="astronaut")
    nutrition_records: Mapped[list["NutritionRecord"]] = relationship(back_populates="astronaut")


class HealthMeasurement(Base):
    __tablename__ = "health_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    identity_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronaut_profiles.id"), index=True)
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(100), default="MANUALLY_ENTERED_DATA")
    data_quality_status: Mapped[str] = mapped_column(String(50), default="VALID")
    mission_context: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    astronaut: Mapped[AstronautProfile] = relationship(back_populates="health_measurements")


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronaut_profiles.id"), index=True)
    mission_day: Mapped[int] = mapped_column(Integer, default=0)
    sleep_duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fatigue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effort: Mapped[int | None] = mapped_column(Integer, nullable=True)
    general_observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    astronaut: Mapped[AstronautProfile] = relationship(back_populates="checkins")


class MissionContext(Base):
    __tablename__ = "mission_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronaut_profiles.id"), index=True)
    mission_day: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(100), default="Routine")
    recent_physical_activity: Mapped[str | None] = mapped_column(Text, nullable=True)
    exercise_sessions: Mapped[str | None] = mapped_column(Text, nullable=True)
    eva_activities: Mapped[str | None] = mapped_column(Text, nullable=True)
    sleep_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    nutrition: Mapped[str | None] = mapped_column(Text, nullable=True)
    environmental_observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevant_events: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    astronaut: Mapped[AstronautProfile] = relationship(back_populates="contexts")


class MissionEvent(Base):
    __tablename__ = "mission_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronaut_profiles.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    mission_day: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class NasaStudy(Base):
    __tablename__ = "nasa_studies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    study_id: Mapped[str] = mapped_column(String(100), index=True, unique=True)
    title: Mapped[str] = mapped_column(String(255))
    source_name: Mapped[str] = mapped_column(String(150), default="NASA")
    source_url: Mapped[str] = mapped_column(String(500))
    organism: Mapped[str] = mapped_column(String(100), default="Human")
    study_type: Mapped[str] = mapped_column(String(100), default="Observational")
    experiment_type: Mapped[str] = mapped_column(String(150), default="Research")
    variables: Mapped[str] = mapped_column(Text, default="")
    space_factors: Mapped[str] = mapped_column(Text, default="")
    data_type: Mapped[str] = mapped_column(String(100), default="Dataset")
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    imported_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_human: Mapped[bool] = mapped_column(default=False)
    is_animal: Mapped[bool] = mapped_column(default=False)
    is_cellular: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportedDataset(Base):
    __tablename__ = "imported_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    study_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    columns: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_label: Mapped[str] = mapped_column(String(150), default="USER_IMPORT")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    status: Mapped[str] = mapped_column(String(60), default="UPLOADED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScientificAnalysisRecord(Base):
    __tablename__ = "scientific_analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_type: Mapped[str] = mapped_column(String(150))
    model_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    input_variables: Mapped[str] = mapped_column(Text)
    run_timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    result_summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    dataset_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScientificReportDocument(Base):
    __tablename__ = "scientific_report_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_type: Mapped[str] = mapped_column(String(150))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExerciseRecord(Base):
    __tablename__ = "exercise_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronaut_profiles.id"), index=True)
    session_name: Mapped[str] = mapped_column(String(200))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mission_day: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class NutritionRecord(Base):
    __tablename__ = "nutrition_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronaut_profiles.id"), index=True)
    meal_name: Mapped[str] = mapped_column(String(200))
    meal_time: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fats_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    hydration_liters: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    astronaut: Mapped[AstronautProfile] = relationship(back_populates="nutrition_records")


class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronaut_profiles.id"), index=True)
    metric_name: Mapped[str] = mapped_column(String(100))
    flag_level: Mapped[str] = mapped_column(String(50))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class GuidanceEntry(Base):
    __tablename__ = "guidance_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    topic: Mapped[str] = mapped_column(String(200))
    body_system: Mapped[str] = mapped_column(String(100))
    related_indicators: Mapped[str] = mapped_column(String(255))
    explanation: Mapped[str] = mapped_column(Text)
    preventive_info: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    last_review_date: Mapped[str] = mapped_column(String(50))


class SensorMetadata(Base):
    __tablename__ = "sensor_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sensor_name: Mapped[str] = mapped_column(String(200))
    sensor_type: Mapped[str] = mapped_column(String(100))
    source_label: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModelAnalysisRecord(Base):
    __tablename__ = "model_analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(150))
    version: Mapped[str] = mapped_column(String(50))
    metrics: Mapped[str] = mapped_column(Text)
    training_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
