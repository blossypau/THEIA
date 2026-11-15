from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config.settings import DEFAULT_ASTRONAUT_NAME, MISSION_ID, DEFAULT_MISSION_DAY
from database.models import (
    AnomalyRecord,
    AstronautProfile,
    DailyCheckin,
    ExerciseRecord,
    GuidanceEntry,
    HealthMeasurement,
    MissionContext,
    MissionEvent,
    NutritionRecord,
)


def ensure_astronaut(session: Session) -> AstronautProfile:
    astronaut = session.query(AstronautProfile).filter_by(mission_id=MISSION_ID).first()
    if astronaut is None:
        astronaut = AstronautProfile(
            name=DEFAULT_ASTRONAUT_NAME,
            mission_id=MISSION_ID,
            mission_day=DEFAULT_MISSION_DAY,
            role="Flight Surgeon Support",
            notes="Experimental mission health monitoring profile.",
        )
        session.add(astronaut)
        session.commit()
        session.refresh(astronaut)
    return astronaut


def seed_sample_data(session: Session) -> AstronautProfile:
    astronaut = ensure_astronaut(session)

    if session.query(HealthMeasurement).count() > 0:
        return astronaut

    base = datetime.utcnow() - timedelta(days=14)
    for i in range(14):
        ts = base + timedelta(days=i, hours=8)
        session.add_all(
            [
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="heart_rate",
                    value=62 + (i % 5),
                    unit="bpm",
                    timestamp=ts,
                    source="SIMULATED_DATA",
                    data_quality_status="VALID",
                    mission_context="Routine check",
                ),
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="blood_pressure",
                    value=118 + (i % 6),
                    unit="mmHg",
                    timestamp=ts,
                    source="MANUALLY_ENTERED_DATA",
                    data_quality_status="VALID",
                    mission_context="Daily measurement",
                ),
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="blood_glucose",
                    value=96 + (i % 3),
                    unit="mg/dL",
                    timestamp=ts,
                    source="SIMULATED_DATA",
                    data_quality_status="VALID",
                    mission_context="Post-breakfast",
                ),
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="body_temperature",
                    value=36.8 + (i % 4) * 0.1,
                    unit="C",
                    timestamp=ts,
                    source="REAL_SENSOR_DATA",
                    data_quality_status="VALID",
                    mission_context="Morning measurement",
                ),
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="sleep_hours",
                    value=7.2 + (i % 3) * 0.3,
                    unit="hours",
                    timestamp=ts,
                    source="MANUALLY_ENTERED_DATA",
                    data_quality_status="VALID",
                    mission_context="Sleep record",
                ),
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="mood",
                    value=72 + (i % 4),
                    unit="score",
                    timestamp=ts,
                    source="MANUALLY_ENTERED_DATA",
                    data_quality_status="VALID",
                    mission_context="Daily check-in",
                ),
            ]
        )

    session.add_all(
        [
            DailyCheckin(
                astronaut_id=astronaut.id,
                mission_day=DEFAULT_MISSION_DAY,
                sleep_duration_hours=7.5,
                sleep_quality=4,
                mood=78,
                energy=72,
                fatigue=26,
                effort=40,
                general_observations="Recovered well after exercise block.",
                symptoms="None",
                timestamp=datetime.utcnow() - timedelta(days=1),
            ),
            DailyCheckin(
                astronaut_id=astronaut.id,
                mission_day=DEFAULT_MISSION_DAY - 1,
                sleep_duration_hours=6.8,
                sleep_quality=3,
                mood=70,
                energy=68,
                fatigue=35,
                effort=55,
                general_observations="Moderate workload with reduced recovery.",
                symptoms="Mild fatigue",
                timestamp=datetime.utcnow() - timedelta(days=2),
            ),
            MissionContext(
                astronaut_id=astronaut.id,
                mission_day=DEFAULT_MISSION_DAY,
                phase="Routine",
                recent_physical_activity="Resistance training and mobility circuit.",
                exercise_sessions="2 sessions logged this week.",
                eva_activities="No EVA scheduled.",
                sleep_history="Sleep duration trending near baseline.",
                nutrition="Meals and hydration tracked with 3 eating windows.",
                environmental_observations="Cabin pressure stable, thermal range normal.",
                relevant_events="Crew briefing completed.",
                timestamp=datetime.utcnow(),
            ),
            MissionEvent(
                astronaut_id=astronaut.id,
                event_type="Exercise",
                description="Strength training and recovery cycle.",
                mission_day=DEFAULT_MISSION_DAY,
                timestamp=datetime.utcnow() - timedelta(hours=5),
            ),
            NutritionRecord(
                astronaut_id=astronaut.id,
                meal_name="Protein oats and fruit",
                meal_time=datetime.utcnow() - timedelta(hours=5),
                calories=420,
                protein_g=18,
                carbs_g=48,
                fats_g=16,
                hydration_liters=0.7,
                estimated=False,
                notes="Breakfast recorded with standard nutrient estimate.",
            ),
            GuidanceEntry(
                topic="Sleep and recovery",
                body_system="Neurological and vestibular",
                related_indicators="sleep_hours,fatigue,mood",
                explanation="Sleep quality influences alertness, mood regulation, and recovery for long-duration missions.",
                preventive_info="Prioritize consistent rest opportunities and evaluate patterns when sleep is below mission thresholds.",
                source="NASA Human Research Program guidance and crew health education materials.",
                last_review_date="2025-01-15",
            ),
        ]
    )

    session.commit()
    return astronaut


def get_latest_measurements(session: Session, metric_names=None):
    metrics = metric_names or ["heart_rate", "blood_pressure", "blood_glucose", "body_temperature", "sleep_hours", "mood"]
    results = []
    for metric in metrics:
        row = session.query(HealthMeasurement).filter_by(metric_name=metric).order_by(HealthMeasurement.timestamp.desc()).first()
        if row:
            results.append(row)
    return results


def get_dashboard_summary(session: Session):
    astronaut = ensure_astronaut(session)
    latest = get_latest_measurements(session)
    latest_checkin = session.query(DailyCheckin).filter_by(astronaut_id=astronaut.id).order_by(DailyCheckin.timestamp.desc()).first()
    anomalies = session.query(AnomalyRecord).filter_by(astronaut_id=astronaut.id).order_by(AnomalyRecord.timestamp.desc()).limit(5).all()
    latest_context = session.query(MissionContext).filter_by(astronaut_id=astronaut.id).order_by(MissionContext.timestamp.desc()).first()
    return {
        "astronaut": astronaut,
        "latest_measurements": latest,
        "latest_checkin": latest_checkin,
        "anomalies": anomalies,
        "latest_context": latest_context,
    }


def get_mission_events(session: Session):
    astronaut = ensure_astronaut(session)
    return session.query(MissionEvent).filter_by(astronaut_id=astronaut.id).order_by(MissionEvent.timestamp.asc()).all()


def get_measurements_for_metric(session: Session, metric_name: str):
    astronaut = ensure_astronaut(session)
    return session.query(HealthMeasurement).filter_by(astronaut_id=astronaut.id, metric_name=metric_name).order_by(HealthMeasurement.timestamp.asc()).all()


def get_daily_checkins(session: Session):
    astronaut = ensure_astronaut(session)
    return session.query(DailyCheckin).filter_by(astronaut_id=astronaut.id).order_by(DailyCheckin.timestamp.desc()).all()


def get_context_records(session: Session):
    astronaut = ensure_astronaut(session)
    return session.query(MissionContext).filter_by(astronaut_id=astronaut.id).order_by(MissionContext.timestamp.desc()).all()


def get_nutrition_records(session: Session):
    astronaut = ensure_astronaut(session)
    return session.query(NutritionRecord).filter_by(astronaut_id=astronaut.id).order_by(NutritionRecord.meal_time.desc()).all()


def get_guidance_entries(session: Session):
    return session.query(GuidanceEntry).all()
