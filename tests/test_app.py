from pathlib import Path
from streamlit.testing.v1 import AppTest
import pytest

@pytest.mark.parametrize('page', ['Mission Overview','Health Dashboard','Health Monitoring','Data Management','Human Body Explorer','Medical Visualization Lab','NASA Data Hub','THEIA Intelligence Center','Personal Baseline','Intelligent Analysis','Mission Reports','Daily Check-in','Mission Timeline','Nutrition','Settings'])
def test_navigation_pages_render(page):
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
    app.radio(key='navigation').set_value(page).run()
    assert not app.exception, [exception.message for exception in app.exception]


def test_data_management_submission_updates_dashboard():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
    app.radio(key='navigation').set_value('Data Management').run()
    app.selectbox(key='entry_metric').set_value('heart_rate').run()
    app.number_input(key='entry_value').set_value(73.0)
    app.button(key='save_measurement').click().run()
    assert not app.exception
    assert any('saved' in item.value for item in app.success)
    app.radio(key='navigation').set_value('Mission Overview').run()
    assert not app.exception
    assert any(metric.value == '73 bpm' for metric in app.metric)
