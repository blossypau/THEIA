from __future__ import annotations

from utils.timestamps import utc_now

from datetime import datetime, timedelta
from contextvars import ContextVar

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
    ImportedDataset,
    MissionContext,
    MissionEvent,
    NasaStudy,
    NutritionRecord,
    ScientificAnalysisRecord,
    ScientificReportDocument,
)


# Scoped per render, reset by the entry point; never shared between browser sessions.
active_astronaut_id: ContextVar[int | None] = ContextVar("active_astronaut_id", default=None)

def ensure_astronaut(session: Session) -> AstronautProfile:
    selected_id = active_astronaut_id.get()
    if selected_id is not None:
        selected = session.get(AstronautProfile, selected_id)
        if selected is None:
            raise ValueError("Selected astronaut profile no longer exists")
        return selected
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

    base = utc_now() - timedelta(days=14)
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
                    source="SIMULATED_DATA",
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
                    source="SIMULATED_DATA",
                    data_quality_status="VALID",
                    mission_context="Morning measurement",
                ),
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="sleep_hours",
                    value=7.2 + (i % 3) * 0.3,
                    unit="hours",
                    timestamp=ts,
                    source="SIMULATED_DATA",
                    data_quality_status="VALID",
                    mission_context="Sleep record",
                ),
                HealthMeasurement(
                    astronaut_id=astronaut.id,
                    metric_name="mood",
                    value=72 + (i % 4),
                    unit="score",
                    timestamp=ts,
                    source="SIMULATED_DATA",
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
                timestamp=utc_now() - timedelta(days=1),
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
                timestamp=utc_now() - timedelta(days=2),
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
                timestamp=utc_now(),
            ),
            MissionEvent(
                astronaut_id=astronaut.id,
                event_type="Exercise",
                description="Strength training and recovery cycle.",
                mission_day=DEFAULT_MISSION_DAY,
                timestamp=utc_now() - timedelta(hours=5),
            ),
            NutritionRecord(
                astronaut_id=astronaut.id,
                meal_name="Protein oats and fruit",
                meal_time=utc_now() - timedelta(hours=5),
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


def get_latest_measurements(session: Session, metric_names=None, astronaut_id=None):
    astronaut_id = astronaut_id or ensure_astronaut(session).id
    metrics = metric_names or ["heart_rate", "blood_pressure", "blood_glucose", "body_temperature", "sleep_hours", "mood"]
    results = []
    for metric in metrics:
        row = session.query(HealthMeasurement).filter_by(astronaut_id=astronaut_id, metric_name=metric).order_by(HealthMeasurement.timestamp.desc(), HealthMeasurement.id.desc()).first()
        if row:
            results.append(row)
    return results


def get_dashboard_summary(session: Session):
    astronaut = ensure_astronaut(session)
    latest = get_latest_measurements(session, astronaut_id=astronaut.id)
    from intelligence.engine import analyze
    analysis = analyze(session, astronaut.id)
    latest_checkin = session.query(DailyCheckin).filter_by(astronaut_id=astronaut.id).order_by(DailyCheckin.timestamp.desc()).first()
    from types import SimpleNamespace
    anomalies = [SimpleNamespace(metric_name=item['metric'], flag_level='STATISTICAL', explanation=f"{flag['timestamp']} | {item['cohort']} | z={flag['z_score']:.2f}") for item in analysis['metrics'].values() for flag in item['anomalies']]
    latest_context = session.query(MissionContext).filter_by(astronaut_id=astronaut.id).order_by(MissionContext.timestamp.desc()).first()
    return {
        "analysis": analysis,
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


def save_health_measurement(session: Session, metric_name: str, value: float, unit: str, source: str = "MANUAL_INPUT", mission_context: str | None = None, notes: str | None = None) -> HealthMeasurement:
    from database.measurements import insert_measurement
    return insert_measurement(session, ensure_astronaut(session).id, dict(metric_name=metric_name, value=value, unit=unit, source=source, timestamp=utc_now(), mission_context=mission_context, notes=notes))


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


def seed_nasa_studies(session: Session) -> list[NasaStudy]:
    if session.query(NasaStudy).count() > 0:
        return session.query(NasaStudy).order_by(NasaStudy.id.asc()).all()

    entries = [
        NasaStudy(
            study_id="HRP-CV-01",
            title="Cardiovascular Adaptations to Spaceflight",
            source_name="NASA Human Research Program",
            source_url="https://www.nasa.gov/hrp/",
            organism="Human",
            study_type="Physiology",
            experiment_type="Cardiovascular monitoring",
            variables="heart_rate,blood_pressure,body_temperature,oxygen_saturation",
            space_factors="Microgravity, workload, recovery",
            data_type="Observational dataset",
            file_url="https://www.nasa.gov/hrp/",
            license_note="Use per NASA public research guidance and source terms.",
            references="NASA HRP; Human Research Roadmap; OSDR evidence catalog.",
            publication_date="2024",
            is_human=True,
            notes="Relevant to cardiovascular physiology, rhythm adaptation, and orthostatic stress monitoring.",
        ),
        NasaStudy(
            study_id="HRP-MSK-01",
            title="Musculoskeletal and Bone Loss in Long-Duration Spaceflight",
            source_name="NASA HRP Evidence Reports",
            source_url="https://humanresearchroadmap.nasa.gov/Evidence/",
            organism="Human",
            study_type="Bone and muscle research",
            experiment_type="Longitudinal health study",
            variables="bone_density,exercise_load,body_mass,physical_performance",
            space_factors="Microgravity, unloading, exercise countermeasures",
            data_type="Research summary",
            file_url="https://humanresearchroadmap.nasa.gov/Evidence/",
            license_note="Public evidence summary; verify source-specific terms.",
            references="NASA HRP, Human Research Roadmap, integrated physiology evidence.",
            publication_date="2024",
            is_human=True,
            notes="Supports musculoskeletal and bone-loss analysis in mission scenarios.",
        ),
        NasaStudy(
            study_id="HRP-SLEEP-01",
            title="Sleep and Circadian Rhythms During Spaceflight",
            source_name="NASA HRP",
            source_url="https://www.nasa.gov/hrp/ongoing-hrp-research/",
            organism="Human",
            study_type="Behavioral and sleep health",
            experiment_type="Circadian rhythm assessment",
            variables="sleep_hours,mood,fatigue,rest_quality",
            space_factors="Confinement, circadian disruption, mission schedule",
            data_type="Behavioral dataset",
            file_url="https://www.nasa.gov/hrp/ongoing-hrp-research/",
            license_note="Public program information and evidence context.",
            references="NASA HRP, behavioral health research notes, mission operations documentation.",
            publication_date="2024",
            is_human=True,
            notes="Supports sleep and recovery analysis for crew performance and habitability studies.",
        ),
        NasaStudy(
            study_id="OSDR-IMM-01",
            title="Immune System and Spaceflight Adaptation",
            source_name="NASA OSDR",
            source_url="https://osdr.nasa.gov/bio/repo/",
            organism="Human",
            study_type="Immunology",
            experiment_type="Biomarker study",
            variables="immune_markers,cytokines,hematology,stress_response",
            space_factors="Spaceflight stress, altered immunity, radiation exposure",
            data_type="Public repository dataset",
            file_url="https://osdr.nasa.gov/bio/repo/",
            license_note="Use according to repository access terms.",
            references="NASA OSDR repository metadata and bioscience data catalog entries.",
            publication_date="2024",
            is_human=True,
            notes="Useful for cross-system analysis where immunologic biomarkers are available.",
        ),
        NasaStudy(
            study_id="HRP-RAD-01",
            title="Space Radiation and Biological Response",
            source_name="NASA Human Research Roadmap",
            source_url="https://humanresearchroadmap.nasa.gov/Risks/",
            organism="Human and cellular",
            study_type="Radiation risk",
            experiment_type="Radiation biology study",
            variables="radiation_exposure,cellular_damage,genomic_response,biomarker_response",
            space_factors="Ionizing radiation, chronic exposure, biological damage",
            data_type="Risk evidence dataset",
            file_url="https://humanresearchroadmap.nasa.gov/Risks/",
            license_note="Evidence and program documentation from NASA, with publication-level attribution required.",
            references="NASA Human Research Roadmap risk pages and evidence summaries.",
            publication_date="2024",
            is_human=True,
            is_cellular=True,
            notes="High-value context for risk modeling, but not interchangeable with clinical human health measurements.",
        ),
    ]
    session.add_all(entries)
    session.commit()
    return session.query(NasaStudy).order_by(NasaStudy.id.asc()).all()


def search_nasa_studies(session: Session, keyword: str = "", organism: str | None = None, study_type: str | None = None):
    query = session.query(NasaStudy)
    if keyword:
        keyword_like = f"%{keyword.lower()}%"
        query = query.filter(
            (func.lower(NasaStudy.title).like(keyword_like))
            | (func.lower(NasaStudy.variables).like(keyword_like))
            | (func.lower(NasaStudy.space_factors).like(keyword_like))
            | (func.lower(NasaStudy.notes).like(keyword_like))
        )
    if organism:
        query = query.filter(func.lower(NasaStudy.organism) == organism.lower())
    if study_type:
        query = query.filter(func.lower(NasaStudy.study_type) == study_type.lower())
    return query.order_by(NasaStudy.title.asc()).all()


def save_imported_dataset(session: Session, study_id: str, file_name: str, file_path: str, columns: str, row_count: int, notes: str | None = None) -> ImportedDataset:
    record = ImportedDataset(
        study_id=study_id,
        file_name=file_name,
        file_path=file_path,
        row_count=row_count,
        columns=columns,
        source_label="USER_IMPORT",
        notes=notes,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_imported_datasets(session: Session):
    return session.query(ImportedDataset).order_by(ImportedDataset.imported_at.desc()).all()


def save_analysis_record(session: Session, analysis_type: str, input_variables: str, result_summary: str, model_name: str | None = None, version: str | None = None, confidence: float | None = None, dataset_source: str | None = None, limitations: str | None = None) -> ScientificAnalysisRecord:
    record = ScientificAnalysisRecord(
        analysis_type=analysis_type,
        model_name=model_name,
        version=version,
        input_variables=input_variables,
        result_summary=result_summary,
        confidence=confidence,
        dataset_source=dataset_source,
        limitations=limitations,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_analysis_records(session: Session):
    return session.query(ScientificAnalysisRecord).order_by(ScientificAnalysisRecord.run_timestamp.desc()).all()


def save_scientific_report(session: Session, report_type: str, title: str, summary: str, file_path: str | None = None, references: str | None = None) -> ScientificReportDocument:
    record = ScientificReportDocument(
        report_type=report_type,
        title=title,
        summary=summary,
        file_path=file_path,
        references=references,
    )
    session.add(record)
    session.flush()
    from database.models import ReportScope
    import json
    try:profile_id=json.loads(summary).get('astronaut_id')
    except (ValueError,TypeError,AttributeError):profile_id=None
    profile_id=profile_id or ensure_astronaut(session).id
    session.add(ReportScope(report_id=record.id,astronaut_id=profile_id))
    session.commit()
    session.refresh(record)
    return record


def get_report_documents(session: Session):
    from database.models import ReportScope
    import json
    profile_id=ensure_astronaut(session).id
    rows=session.query(ScientificReportDocument).order_by(ScientificReportDocument.generated_at.desc()).all()
    result=[]
    for row in rows:
        scope=session.get(ReportScope,row.id)
        if scope is not None:
            if scope.astronaut_id==profile_id:result.append(row)
        else:
            try:
                if json.loads(row.summary or '{}').get('astronaut_id')==profile_id:result.append(row)
            except (ValueError,AttributeError):pass
    return result
