"""Verify an explicitly selected hosted THEIA synthetic demo, including real 3D/CT rendering."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from services.public_dicom import fetch_sample


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--output',default='tmp/public-demo/browser')
    args=parser.parse_args();origin=args.url.rstrip('/');parsed=urlsplit(origin)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:raise ValueError('Provide only the demo origin')
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost'}):raise ValueError('Hosted checks require HTTPS')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    result={};errors=[];local_requests=[]
    with sync_playwright() as p,tempfile.TemporaryDirectory(prefix='theia-public-ct-') as temporary:
        sample=Path(temporary)/'public-ct.dcm';sample.write_bytes(fetch_sample())
        browser=p.chromium.launch(headless=True,args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1600,'height':1300},reduced_motion='reduce')
        page.on('pageerror',lambda error:errors.append(str(error)))
        def request(req):
            host=urlsplit(req.url).hostname
            if host in {'localhost','127.0.0.1','::1'} and host!=parsed.hostname:local_requests.append(req.url)
        page.on('request',request)
        def ready(name):
            page.locator('.workspace-footer').filter(has_text=name).wait_for(timeout=120000)
            assert not page.locator('[data-testid=stException]').count(),page.locator('body').inner_text()[-2500:]
        def nav(name):
            page.get_by_text(name,exact=True).click();ready(name);print('Verified '+name,flush=True)
        def capture(name):page.screenshot(path=str(out/name),timeout=60000,animations='disabled')
        page.goto(origin+'/app/',wait_until='domcontentloaded');ready('Mission Overview')
        assert page.get_by_label('Synthetic scenario workspace',exact=True).is_disabled()
        assert page.get_by_text('SYNTHETIC SCENARIO WORKSPACE',exact=False).count()
        result['forced_synthetic_mode']=True;capture('public-mission-control.png')
        nav('Mission Scenario Mode')
        slider=page.locator('.st-key-replay_speed').get_by_role('slider');slider.focus();slider.press('End')
        page.get_by_role('button',name='Start automatic scenario',exact=True).click()
        page.wait_for_function("Array.from(document.querySelectorAll('.readout')).find(e=>e.textContent.includes('SYNTHETIC OBSERVATIONS'))?.querySelector('.readout-value').textContent==='250'",timeout=120000)
        page.get_by_role('button',name='Stop acquisition',exact=True).click();result['automatic_acquisition']=True
        nav('Human Body Explorer')
        body_frames=[f for f in page.frames if f.url.rstrip('/')==origin+'/visuals']
        body=body_frames[0] if body_frames else page.wait_for_event('framenavigated',predicate=lambda f:f.url.rstrip('/')==origin+'/visuals',timeout=120000)
        body.wait_for_function('window.__THEIA_MODEL_DEBUG__?.count===826',timeout=120000)
        page.get_by_role('combobox',name='Available model structure (keyboard alternative)',exact=True).click()
        page.get_by_role('option',name='Parietal bone.001',exact=True).click()
        body.wait_for_function("window.__THEIA_MODEL_DEBUG__.snapshot().selected==='Parietal bone.001'",timeout=60000)
        body.get_by_role('button',name='Isolate selected',exact=True).click()
        body.wait_for_function('window.__THEIA_MODEL_DEBUG__.snapshot().visible===1')
        body.get_by_role('button',name='Show all structures',exact=True).click()
        result['public_anatomy_826_selection_isolation']=True;capture('public-anatomy.png')
        nav('Medical Visualization Lab')
        frames=[f for f in page.frames if f.url.startswith(origin+'/local')]
        viewer=frames[0] if frames else page.wait_for_event('framenavigated',predicate=lambda f:f.url.startswith(origin+'/local'),timeout=120000)
        viewer.locator('input[type=file]').first.set_input_files(str(sample),timeout=120000)
        viewer.get_by_text('gray, encode',exact=True).dblclick(timeout=120000)
        viewer.locator('canvas').first.wait_for(timeout=120000);page.wait_for_timeout(3000)
        result['public_ohif_ct_rendered']=True;capture('public-ohif.png')
        nav('Data Management');assert page.get_by_text('PUBLIC SYNTHETIC DEMO:',exact=False).count()
        result['personal_imports_disabled']=True
        # A second browser context must start with its own 150-observation fictional seed.
        second=browser.new_page(viewport={'width':1280,'height':1000},reduced_motion='reduce')
        second.goto(origin+'/app/');second.locator('.workspace-footer').wait_for(timeout=120000)
        second.get_by_text('Mission Scenario Mode',exact=True).click()
        second.wait_for_function("Array.from(document.querySelectorAll('.readout')).find(e=>e.textContent.includes('SYNTHETIC OBSERVATIONS'))?.querySelector('.readout-value').textContent==='150'",timeout=120000)
        result['independent_browser_storage']=True;second.close()
        result['javascript_errors']=errors;result['visitor_localhost_requests']=local_requests
        assert not errors and not local_requests,(errors,local_requests)
        (out/'verification.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2),flush=True);browser.close()


if __name__=='__main__':main()
