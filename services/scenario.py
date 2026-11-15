"""Reproducible synthetic workspaces. Real SessionLocal storage is never reset."""
from contextlib import contextmanager
from datetime import datetime,timedelta
from functools import lru_cache
from threading import RLock
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from config.settings import ROOT_DIR, MISSION_ID
from database.database import Base, sqlite_options
from database.models import AstronautProfile, HealthMeasurement, ScientificAnalysisRecord, ScientificReportDocument, MissionEvent
from database.measurements import insert_measurement

ANCHOR=datetime(2026,1,1,8)
PROFILES=[('Astra / Recovery scenario',MISSION_ID),('Mira / Workload scenario','THEIA-SYNTHETIC-02')]


def seed_scenario(session):
    from database.models import SchemaMigration
    if session.get(SchemaMigration,'5.0-additive-context-provenance') is None:
        session.add(SchemaMigration(version='5.0-additive-context-provenance'))
    for index,(name,mission) in enumerate(PROFILES):
        profile=AstronautProfile(name=name,mission_id=mission,mission_day=30,role='Synthetic demonstration profile',notes='THEIA_SCENARIO_V1: exclusively synthetic observations')
        session.add(profile);session.flush()
        for day in range(30):
            values={'heart_rate':(64+index*8+(day%7)*.6,'bpm'),'sleep_hours':(7.6-index*.8-(day%5)*.12,'hours'),
                'fatigue':(22+index*10+(day%7)*.8,'score'),'oxygen_saturation':(98-(day%3)*.2,'%'),
                'body_temperature':(36.7+(day%4)*.07,'C')}
            for metric,(value,unit) in values.items():
                insert_measurement(session,profile.id,dict(metric_name=metric,value=value,unit=unit,timestamp=ANCHOR+timedelta(days=day),source='SIMULATED_DATA',mission_context='Reproducible synthetic mission scenario'),commit=False)
        session.add(MissionEvent(astronaut_id=profile.id,event_type='Synthetic scenario',description='Deterministic 30-day reference dataset. No real crew telemetry.',mission_day=30,timestamp=ANCHOR+timedelta(days=29)))
    session.commit()


_creation_lock=RLock()


@lru_cache(maxsize=32)
def scenario_factory(workspace_id, root=None):
    identifier=UUID(str(workspace_id)).hex
    directory=Path(root or ROOT_DIR/'tmp/scenarios')/identifier
    # lru_cache can call its wrapped function concurrently on the same cache miss.
    # Serialize schema creation and seed so overlapping Streamlit reruns cannot race.
    with _creation_lock:
        directory.mkdir(parents=True,exist_ok=True)
        engine=create_engine(f'sqlite:///{directory / "scenario.sqlite3"}',connect_args={'timeout':30})
        event.listen(engine,'connect',sqlite_options)
        Base.metadata.create_all(engine)
        factory=sessionmaker(bind=engine,autoflush=False,info={'scenario':True,'scenario_dir':str(directory)})
        with factory() as session:
            if not session.query(AstronautProfile).count():seed_scenario(session)
        return factory


def reset_scenario(session):
    if not session.info.get('scenario'):
        raise ValueError('Reset is only permitted in an isolated synthetic workspace')
    if Path(session.get_bind().url.database).resolve() != (Path(session.info['scenario_dir'])/'scenario.sqlite3').resolve():
        raise ValueError('Scenario storage identity mismatch; reset refused')
    profiles=session.query(AstronautProfile).all()
    if any(not (p.notes or '').startswith('THEIA_SCENARIO_V1:') for p in profiles):
        raise ValueError('Unrecognized profile in scenario; reset refused')
    if session.query(HealthMeasurement).filter(HealthMeasurement.source!='SIMULATED_DATA').count():
        raise ValueError('Non-synthetic measurements detected; reset refused')
    # Delete only rows from this separately routed workspace, never filesystem paths.
    from database import models
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.flush();session.expunge_all();seed_scenario(session)
    from services.retention import cleanup_scenario_artifacts
    cleanup_scenario_artifacts(session,older_than_days=0)
    from services.test_sync import reset_mirror
    reset_mirror(session)


def add_scenario_measurement(session, astronaut_id, metric='fatigue', value=80):
    if not session.info.get('scenario'):raise ValueError('Synthetic scenario session required')
    from utils.measurement_schema import UNIT_BY_METRIC
    if metric not in {'fatigue','sleep_hours','heart_rate'}:raise ValueError('Unsupported scenario signal')
    latest=session.query(HealthMeasurement).filter_by(astronaut_id=astronaut_id).order_by(HealthMeasurement.timestamp.desc()).first()
    timestamp=(latest.timestamp+timedelta(days=1)) if latest else ANCHOR
    return insert_measurement(session,astronaut_id,dict(metric_name=metric,value=value,unit=next(iter(UNIT_BY_METRIC[metric])),timestamp=timestamp,source='SIMULATED_DATA',mission_context='Synthetic scenario intervention'))
