from datetime import datetime
from pathlib import Path
from uuid import uuid4
import pytest
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest
from database.database import SessionLocal, session_factory_override, init_db
from database.models import HealthMeasurement, AstronautProfile
from database.repository import ensure_astronaut,get_dashboard_summary,active_astronaut_id
from services.scenario import scenario_factory,add_scenario_measurement,reset_scenario
from services.anatomy import structure_registry,anatomy_view
from intelligence.engine import analyze
from modules.reports.reports import generate_pdf_report


def test_scenario_end_to_end_and_real_storage_is_unchanged(tmp_path):
    init_db()
    with SessionLocal() as real:
        original=(real.query(HealthMeasurement).count(),real.query(AstronautProfile).count())
    factory=scenario_factory(str(uuid4()),str(tmp_path))
    token=session_factory_override.set(factory)
    try:
        with SessionLocal() as session:
            astronaut=ensure_astronaut(session)
            before=analyze(session,astronaut.id)
            assert before['quality']['total']==150
            record=add_scenario_measurement(session,astronaut.id)
            after=analyze(session,astronaut.id)
            assert after['quality']['total']==151 and before['fingerprint']!=after['fingerprint']
            flag=next(flag for flag in after['metrics']['fatigue:simulated']['anomalies'] if flag['id']==record.id)
            assert flag['value']==80 and flag['quality']=='VALID' and flag['samples']==31
            assert flag['deviation']==pytest.approx(80-flag['baseline_mean'])
            assert len(after['metrics'][flag['input_cohort']]['measurement_ids'])==31 and 'z_score' in flag['methods']
            assert all('measurement_ids' not in candidate for item in after['metrics'].values() for candidate in item['anomalies'])
            assert get_dashboard_summary(session)['analysis']==after
            identifier=next(iter(structure_registry()))
            assert anatomy_view(session,astronaut.id,identifier)['analysis']==after
            pdf=generate_pdf_report(session)
            assert str(pdf).startswith(str(tmp_path))
            text='\n'.join(page.extract_text() for page in PdfReader(pdf).pages)
            assert after['fingerprint'] in text and '80.000' in text
            reset_scenario(session)
            restored=analyze(session,ensure_astronaut(session).id)
            assert restored['fingerprint']==before['fingerprint']
            assert session.query(HealthMeasurement).count()==300
    finally:session_factory_override.reset(token)
    with SessionLocal() as real:
        assert (real.query(HealthMeasurement).count(),real.query(AstronautProfile).count())==original
        with pytest.raises(ValueError):reset_scenario(real)


def test_scenario_rejects_path_injection_and_unsafe_reset(tmp_path):
    with pytest.raises(ValueError):scenario_factory('../../real-data',str(tmp_path))
    factory=scenario_factory(str(uuid4()),str(tmp_path))
    with factory() as session:
        first=session.query(HealthMeasurement).first();first.source='REAL_SENSOR_DATA';session.commit()
        count=session.query(HealthMeasurement).count()
        with pytest.raises(ValueError,match='Non-synthetic'):reset_scenario(session)
        assert session.query(HealthMeasurement).count()==count


def test_scenario_ui_switch_add_pdf_reset_and_return_to_real():
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=45).run()
    real_profile=app.selectbox(key='active_astronaut').value
    app.toggle(key='scenario_mode').set_value(True).run()
    app.radio(key='navigation').set_value('Mission Scenario Mode').run()
    assert not app.exception
    app.button(key='scenario_add').click().run()
    assert not app.exception
    assert any('Synthetic measurement' in item.value for item in app.success)
    app.button(key='scenario_pdf_generate').click().run()
    assert not app.exception and app.session_state['scenario_pdf_bytes'].startswith(b'%PDF')
    app.radio(key='navigation').set_value('THEIA Intelligence Center').run()
    app.selectbox(key='intelligence_metric').set_value('fatigue').run()
    assert not app.exception
    assert any('fatigue / 80' in item.label for item in app.expander)
    app.radio(key='navigation').set_value('Mission Scenario Mode').run()
    app.button(key='scenario_reset').click().run()
    assert not app.exception
    assert any('reset to the deterministic' in item.value for item in app.success)
    app.toggle(key='scenario_mode').set_value(False).run()
    assert not app.exception and app.selectbox(key='active_astronaut').value==real_profile


def test_synthetic_sessions_are_isolated_and_csv_is_refused(tmp_path):
    from integrations.csv_import import import_csv
    import io
    first=scenario_factory(str(uuid4()),str(tmp_path))
    second=scenario_factory(str(uuid4()),str(tmp_path))
    with first() as session:
        add_scenario_measurement(session,1)
        assert session.query(HealthMeasurement).filter_by(astronaut_id=1).count()==151
        from services.datasets import register_table
        table,_=register_table(session,b'name,value\nsynthetic,1\n','synthetic.csv')
        assert str(table.file_path).startswith(session.info['scenario_dir'])
        with pytest.raises(ValueError,match='CSV import is disabled'):
            import_csv(session,io.BytesIO(b'metric_name,value,unit,timestamp\nheart_rate,75,bpm,2026-01-01'))
    with second() as session:
        assert session.query(HealthMeasurement).filter_by(astronaut_id=1).count()==150
        assert {row.source for row in session.query(HealthMeasurement)}=={'SIMULATED_DATA'}
