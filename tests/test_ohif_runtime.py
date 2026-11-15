"""OHIF readiness distinguishes an occupied port from a usable viewer."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
import socket

import pytest
import requests
from services.viewer_server import ViewerHandler
from services.ohif_runtime import probe_ohif, resolve_ohif, remember_service, workspace_id
from scripts import start_theia_services as launcher


@pytest.fixture
def build(tmp_path):
    (tmp_path / 'index.html').write_text('<html><script src="app.js"></script>OHIF</html>')
    (tmp_path / 'app.js').write_text('window.ohifTest=true;')
    # Deliberately plausible config: a phrase match must not accept a generic static server.
    (tmp_path / 'app-config.js').write_text('// Local files only')
    return tmp_path


@pytest.fixture
def serve():
    servers=[]
    def start(handler, directory):
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(handler,directory=str(directory)))
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        servers.append((server,thread))
        return f'http://127.0.0.1:{server.server_port}',server.server_port
    yield start
    for server,thread in servers:
        server.shutdown();server.server_close();thread.join()


def test_old_static_server_is_not_ready_even_with_config_phrase(build,serve):
    url,_=serve(SimpleHTTPRequestHandler,build)
    assert requests.get(url+'/app-config.js').status_code==200
    status=probe_ohif(url)
    assert not status.ready and 'HTTP 404' in status.reason


def test_compatible_server_and_discovery(build,serve,tmp_path,monkeypatch):
    monkeypatch.delenv('THEIA_OHIF_URL',raising=False)
    url,_=serve(ViewerHandler,build)
    state=tmp_path/'runtime.json'
    remember_service(url,state)
    status=resolve_ohif(state)
    assert status.ready and status.viewer_url==url+'/local'


def test_missing_bundle_and_bad_spa_are_not_ready(build,serve):
    url,_=serve(ViewerHandler,build)
    (build/'app.js').unlink()
    assert not probe_ohif(url).ready
    (build/'app.js').write_text('window.test=true;')
    class MissingRoute(ViewerHandler):
        def do_GET(self):
            if self.path=='/local': self.send_error(404)
            else: super().do_GET()
    url,_=serve(MissingRoute,build)
    assert not probe_ohif(url).ready


def test_healthy_existing_server_is_reused(build,serve,tmp_path,monkeypatch):
    url,_=serve(ViewerHandler,build)
    monkeypatch.delenv('THEIA_OHIF_URL',raising=False)
    monkeypatch.setattr(launcher,'DEFAULT_URL',url)
    def forbidden(*args,**kwargs): raise AssertionError('Existing healthy server must be reused')
    monkeypatch.setattr(launcher.subprocess,'Popen',forbidden)
    status,process=launcher.ensure_ohif(build,tmp_path/'runtime.json')
    assert status.ready and process is None


def test_occupied_incompatible_port_uses_safe_fallback(build,serve,tmp_path,monkeypatch):
    old_url,old_port=serve(SimpleHTTPRequestHandler,build)
    monkeypatch.delenv('THEIA_OHIF_URL',raising=False)
    monkeypatch.setattr(launcher,'DEFAULT_URL',old_url)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); free_port=sock.getsockname()[1]
    state=tmp_path/'runtime.json'
    status,process=launcher.ensure_ohif(build,state,ports=[old_port,free_port],ready_timeout=10)
    try:
        assert process is not None and status.ready and status.base_url.endswith(':'+str(free_port))
        assert requests.get(old_url+'/',timeout=2).status_code==200  # unrelated listener survives
        assert resolve_ohif(state).ready
    finally:
        if process is not None:
            process.terminate();process.wait(timeout=10)
    # A stale discovery record must not remain falsely ready.
    assert not probe_ohif(status.base_url).ready


def test_explicit_url_is_honored_and_discovery_rejects_external_urls(build,serve,tmp_path,monkeypatch):
    url,_=serve(SimpleHTTPRequestHandler,build)
    monkeypatch.setenv('THEIA_OHIF_URL',url)
    assert not resolve_ohif(tmp_path/'runtime.json').ready
    with pytest.raises(ValueError): remember_service('https://example.com',tmp_path/'runtime.json')
    monkeypatch.setenv('THEIA_OHIF_URL','http://127.0.0.1:1')
    assert not resolve_ohif(tmp_path/'missing.json').ready


def test_medical_lab_uses_discovered_url(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from services.ohif_runtime import ViewerStatus
    import modules.medical_visualization_lab.medical_visualization_lab as lab
    monkeypatch.setattr(lab,'resolve_ohif',lambda: ViewerStatus('http://127.0.0.1:3009',True,'verified'))
    def app():
        from modules.medical_visualization_lab.medical_visualization_lab import render_medical_visualization_lab
        render_medical_visualization_lab()
    rendered=AppTest.from_function(app,default_timeout=15).run()
    assert not rendered.exception
    assert rendered.success
    assert any('3009/local' in caption.value for caption in rendered.caption)
    assert rendered.get('iframe')[0].proto.src == 'http://127.0.0.1:3009/local'


def test_medical_lab_shows_specific_failure_without_embedding(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from services.ohif_runtime import ViewerStatus
    import modules.medical_visualization_lab.medical_visualization_lab as lab
    monkeypatch.setattr(lab,'resolve_ohif',lambda: ViewerStatus('http://127.0.0.1:3001',False,'HTTP 404: legacy static server'))
    def app():
        from modules.medical_visualization_lab.medical_visualization_lab import render_medical_visualization_lab
        render_medical_visualization_lab()
    rendered=AppTest.from_function(app,default_timeout=15).run()
    assert not rendered.exception
    assert 'HTTP 404' in rendered.warning[0].value
    assert not rendered.get('iframe')
    assert '--ohif-only' in rendered.code[0].value
