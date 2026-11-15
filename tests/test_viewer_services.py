from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
import requests
from services.viewer_server import ViewerHandler
from services.theia_integration_api import TheiaBridgeHandler
from services.anatomy import structure_registry
from urllib.parse import quote


def test_ohif_spa_headers_and_local_only_config(tmp_path):
    (tmp_path/'index.html').write_text('<html>OHIF test build</html>')
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(ViewerHandler,directory=str(tmp_path)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        response=requests.get(base+'/local',timeout=3)
        assert response.ok and 'OHIF test build' in response.text
        assert response.headers['Cross-Origin-Opener-Policy'] == 'same-origin'
        assert response.headers['Cross-Origin-Embedder-Policy'] == 'credentialless'
        config=requests.get(base+'/app-config.js',timeout=3).text
        assert "defaultDataSourceName: 'dicomlocal'" in config
        assert 'dicomweb' not in config and 'https://' not in config
    finally:
        server.shutdown();server.server_close();thread.join()


def test_bridge_real_identifiers_and_no_global_selection():
    server=ThreadingHTTPServer(('127.0.0.1',0),TheiaBridgeHandler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        assert requests.get(base+'/health',timeout=3).json()['status'] == 'ok'
        assert requests.get(base+'/api/selection',timeout=3).json()['selection'] is None
        identifier=next(iter(structure_registry()))
        assert requests.get(base+'/api/organ/'+quote(identifier),timeout=3).json()['identifier'] == identifier
        assert requests.get(base+'/api/organ/invented-heart',timeout=3).status_code == 404
        assert requests.post(base+'/api/selection',json={'organ':'Heart'},timeout=3).status_code == 410
    finally:
        server.shutdown();server.server_close();thread.join()
