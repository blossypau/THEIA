"""The public listener exposes demo assets, never normal storage or visitor-local services."""
import asyncio
from pathlib import Path
import pytest
from starlette.applications import Starlette
from services.public_demo import gateway


def request(app,path,method='GET'):
    messages=[]
    async def run():
        async def receive():return {'type':'http.request','body':b'','more_body':False}
        async def send(message):messages.append(message)
        await app({'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1',
            'method':method,'scheme':'https','path':path,'raw_path':path.encode(),'root_path':'',
            'query_string':b'','headers':[(b'host',b'theia.example')],
            'server':('theia.example',443),'client':('192.0.2.1',1)},receive,send)
    asyncio.run(run())
    start=next(m for m in messages if m['type']=='http.response.start')
    return start['status'],dict(start['headers']),b''.join(m.get('body',b'') for m in messages)


@pytest.fixture
def app(tmp_path):
    (tmp_path/'index.html').write_text('<html>OHIF fixture</html>')
    (tmp_path/'app.js').write_text('// public build fixture')
    return gateway(Starlette(),tmp_path)


@pytest.mark.parametrize('path',['/theia.db','/.env','/database/models.py','/../config/settings.py','/visuals/../../theia.db'])
def test_no_project_or_database_files_are_served(app,path):
    assert request(app,path)[0]==404


@pytest.mark.parametrize('path',['/app/_stcore/agent/interact','/app/_stcore/upload_file/session/file'])
def test_agent_and_upload_endpoints_blocked(app,path):
    assert request(app,path,'POST')[0]==403


def test_same_origin_assets_health_and_viewer(app):
    status,headers,body=request(app,'/visuals/')
    assert status==200 and b'viewer.js' in body
    assert request(app,'/visuals/body.glb','HEAD')[0]==200
    assert request(app,'/theia/health')[0]==200 and request(app,'/local')[0]==200
    assert request(app,'/app-config.js')[0]==200
    assert headers[b'cross-origin-opener-policy']==b'same-origin'
    assert request(app,'/')[1][b'location']==b'/app/'


def test_missing_ohif_does_not_hide_anatomy(tmp_path):
    app=gateway(Starlette(),tmp_path)
    assert request(app,'/theia/health')[0]==503
    assert request(app,'/local')[0]==503
    assert request(app,'/visuals/')[0]==200 and request(app,'/health')[0]==200


def test_public_mode_rejects_normal_storage(monkeypatch):
    from database.database import SessionLocal
    monkeypatch.setenv('THEIA_PUBLIC_DEMO','1')
    with pytest.raises(RuntimeError,match='normal database'):SessionLocal()


def test_public_ui_forces_synthetic_and_disables_personal_entry(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('THEIA_PUBLIC_DEMO','1')
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=45).run()
    assert not app.exception and app.toggle(key='scenario_mode').value
    assert app.toggle(key='scenario_mode').disabled
    app.radio(key='navigation').set_value('Data Management').run()
    assert not app.exception and any('PUBLIC SYNTHETIC DEMO' in i.value for i in app.info)
    assert not app.file_uploader


@pytest.mark.parametrize('unsafe',[False,True])
def test_pinned_viewer_installer_validates_and_preserves(tmp_path,monkeypatch,unsafe):
    import io,zipfile,json,hashlib
    import scripts.install_ohif_runtime as installer
    content=io.BytesIO()
    with zipfile.ZipFile(content,'w') as archive:
        archive.writestr('index.html','public fixture');archive.writestr('app.js','// public fixture')
        archive.writestr('LICENSE','MIT license fixture')
        if unsafe:archive.writestr('../outside.txt','refused')
    data=content.getvalue();(tmp_path/'config').mkdir()
    (tmp_path/'config/ohif-runtime.json').write_text(json.dumps({'url':'https://example.invalid/runtime.zip','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))
    monkeypatch.setattr(installer,'ROOT',tmp_path)
    monkeypatch.setattr(installer.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(data))
    if unsafe:
        with pytest.raises(ValueError,match='Unsafe'):installer.install(tmp_path/'dist')
        assert not (tmp_path/'outside.txt').exists()
    else:
        destination=installer.install(tmp_path/'dist');assert (destination/'app.js').exists()
        monkeypatch.setattr(installer.urllib.request,'urlopen',lambda *a,**kw:pytest.fail('Existing build must be preserved'))
        assert installer.install(tmp_path/'dist')==destination
