from pathlib import Path
from datetime import datetime
from streamlit.testing.v1 import AppTest
from database.database import SessionLocal,init_db
from database.models import AstronautProfile
from database.repository import ensure_astronaut,active_astronaut_id,get_dashboard_summary
from database.measurements import insert_measurement,measurement_frame
from modules.reports.reports import generate_pdf_report
from pypdf import PdfReader

APP=Path(__file__).resolve().parents[1]/'app.py'


def test_astronaut_switch_scopes_views_entry_and_reports(tmp_path):
    init_db()
    with SessionLocal() as session:
        original=ensure_astronaut(session)
        other=AstronautProfile(name='UI synthetic crew',mission_id='UI-TEST',mission_day=12)
        session.add(other);session.commit();other_id=other.id;original_id=original.id
        insert_measurement(session,other_id,dict(metric_name='heart_rate',value=81,unit='bpm',timestamp=datetime(2026,1,1),source='SIMULATED_DATA'))
    app=AppTest.from_file(APP,default_timeout=30).run()
    app.selectbox(key='active_astronaut').set_value(other_id).run()
    assert not app.exception
    assert any(metric.value=='81 bpm' for metric in app.metric)
    app.radio(key='navigation').set_value('Data Management').run()
    app.selectbox(key='entry_metric').set_value('heart_rate').run()
    app.number_input(key='entry_value').set_value(82)
    app.button(key='save_measurement').click().run()
    assert not app.exception and app.success
    # Entry goes to the selected astronaut; per-render context cannot leak afterward.
    assert active_astronaut_id.get() is None
    with SessionLocal() as session:
        assert 82 in measurement_frame(session,other_id).value.tolist()
        token=active_astronaut_id.set(other_id)
        try:
            summary=get_dashboard_summary(session)
            assert summary['astronaut'].id==other_id
            pdf=generate_pdf_report(session,output_path=tmp_path/'scoped.pdf')
            assert 'UI synthetic crew' in '\n'.join(p.extract_text() for p in PdfReader(pdf).pages)
        finally:active_astronaut_id.reset(token)
        assert ensure_astronaut(session).id==original_id
    app.radio(key='navigation').set_value('Health Dashboard').run()
    app.segmented_control(key='health_period').set_value('7 days').run()
    assert not app.exception
    app.radio(key='navigation').set_value('Human Body Explorer').run()
    assert not app.exception


def test_command_shortcuts_navigate():
    app=AppTest.from_file(APP,default_timeout=30).run()
    app.button(key='overview_anatomy').click().run()
    assert app.radio(key='navigation').value=='Human Body Explorer'
    assert not app.exception
    app.button(key='anatomy_to_health').click().run()
    assert app.radio(key='navigation').value=='Health Dashboard'
    assert not app.exception
