"""Opt-in end-to-end verification of the synthetic mission, including public DICOM.

Requires a running local THEIA, Playwright Chromium, pydicom and pypdf.
Only the browser's isolated synthetic workspace is changed.
"""
import argparse
import json
import sys
from pathlib import Path
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from services.public_dicom import fetch_sample
from services.ohif_runtime import resolve_ohif


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8507')
    parser.add_argument('--output',default='tmp/theia51/browser')
    args=parser.parse_args()
    from urllib.parse import urlsplit
    if urlsplit(args.url).hostname not in {'localhost','127.0.0.1'}:raise ValueError('Use a local THEIA instance')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True);result={};errors=[]
    with tempfile.TemporaryDirectory(prefix='theia5-public-ct-') as directory,sync_playwright() as p:
        sample=Path(directory)/'public-ct.dcm';sample.write_bytes(fetch_sample())
        browser=p.chromium.launch(headless=True,args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1600,'height':1800},reduced_motion='reduce');page.on('pageerror',lambda e:errors.append(str(e)))
        def finish(name):
            page.locator('.workspace-footer').filter(has_text=name).wait_for(timeout=60000)
            page.get_by_text('Stop',exact=True).wait_for(state='hidden',timeout=60000)
            assert not page.locator('[data-testid=stException]').count(),page.locator('body').inner_text()[-3000:]
        def nav(name):
            page.get_by_text(name,exact=True).click();finish(name)
            print('Verified workspace: '+name,flush=True)
        def choose(label,value):
            page.get_by_role('combobox',name=label,exact=True).click();page.get_by_role('option',name=value,exact=True).click()
            page.get_by_text('Stop',exact=True).wait_for(state='hidden',timeout=60000)
        def capture(name):
            page.evaluate("document.querySelectorAll('*').forEach(e=>{if(e.scrollTop>0)e.scrollTop=0})")
            page.screenshot(path=str(out/name),animations='disabled',timeout=60000)
            print('Captured: '+name,flush=True)
        page.goto(args.url,wait_until='networkidle');finish('Mission Overview')
        normal_provenance=page.get_by_text('PROVENANCE /',exact=False).first.inner_text()
        page.get_by_text('Synthetic scenario workspace',exact=True).click();finish('Mission Overview')
        nav('Mission Scenario Mode')
        slider=page.locator('.st-key-replay_speed').get_by_role('slider');slider.focus();slider.press('End')
        page.get_by_role('button',name='Start automatic scenario',exact=True).click()
        page.wait_for_function("Array.from(document.querySelectorAll('.readout')).find(e=>e.textContent.includes('SYNTHETIC OBSERVATIONS'))?.querySelector('.readout-value').textContent==='250'",timeout=120000)
        page.get_by_role('button',name='Stop acquisition',exact=True).click();finish('Mission Scenario Mode')
        result['automatic_100_measurements']=True;capture('automatic-scenario.png')
        nav('Mission Overview');capture('mission-control.png')
        assert page.get_by_role('button',name='Explore evidence and data',exact=True).count()==5
        result['five_hazards_connected']=True
        nav('THEIA Intelligence Center');choose('Analysis indicator','fatigue')
        page.get_by_text('Independent historical reference',exact=True).wait_for();capture('intelligence-center.png')
        nav('Scientific Analysis');choose('Scientific tool','Mission context & hazards')
        choose('Spaceflight hazard','Space Radiation');capture('radiation.png')
        choose('Spaceflight hazard','Distance from Earth')
        page.get_by_text('SIMULATED test link available',exact=True).click()
        page.get_by_role('button',name='Synchronize to local test SQLite mirror',exact=True).click()
        page.get_by_text('Stop',exact=True).wait_for(state='hidden')
        assert '"sent":20' in page.locator('[data-testid=stJson]').last.inner_text().replace(' ','').replace('\n','')
        result['local_outbox_sync']=True
        choose('Spaceflight hazard','Hostile/Closed Environments');capture('environment.png')
        nav('Human Body Explorer');choose('Available model structure (keyboard alternative)','Parietal bone.001')
        page.get_by_text('Real mesh ID: Parietal bone.001',exact=False).wait_for(timeout=30000)
        viewer=next(f for f in page.frames if f.url=='http://127.0.0.1:3004/')
        viewer.wait_for_function('window.__THEIA_MODEL_DEBUG__?.count===826',timeout=90000)
        viewer.get_by_role('button',name='Isolate selected',exact=True).click()
        viewer.get_by_role('button',name='Show all structures',exact=True).wait_for()
        viewer.get_by_role('button',name='Show all structures',exact=True).click()
        viewer.wait_for_function('window.__THEIA_MODEL_DEBUG__.snapshot().visible===826')
        canvas=viewer.locator('canvas').first
        before=viewer.evaluate('window.__THEIA_MODEL_DEBUG__.snapshot().camera')
        box=canvas.bounding_box();assert box
        page.mouse.move(box['x']+box['width']*.5,box['y']+box['height']*.45)
        page.mouse.down();page.mouse.move(box['x']+box['width']*.65,box['y']+box['height']*.50,steps=10);page.mouse.up()
        page.wait_for_timeout(700)
        assert before!=viewer.evaluate('window.__THEIA_MODEL_DEBUG__.snapshot().camera')
        before=viewer.evaluate('window.__THEIA_MODEL_DEBUG__.snapshot().camera')
        page.mouse.wheel(0,-150);page.wait_for_timeout(700)
        assert before!=viewer.evaluate('window.__THEIA_MODEL_DEBUG__.snapshot().camera')
        viewer.locator('#opacity-control').evaluate("e=>{e.value=.25;e.dispatchEvent(new Event('input',{bubbles:true}))}")
        assert min(viewer.evaluate('window.__THEIA_MODEL_DEBUG__.snapshot().opacity'))<=.25
        result['anatomy_rotation_zoom_opacity']=True
        capture('anatomy.png');result['anatomy_826_isolation_selection']=True
        viewer.locator('#reset-btn').click()
        viewer.wait_for_function('window.__THEIA_MODEL_DEBUG__.snapshot().selected===null && window.__THEIA_MODEL_DEBUG__.snapshot().visible===826',timeout=30000)
        assert all(abs(v-.48)<.001 for v in viewer.evaluate('window.__THEIA_MODEL_DEBUG__.snapshot().opacity'))
        result['anatomy_restore']=True
        nav('Medical Visualization Lab');status=resolve_ohif();assert status.ready
        candidates=[f for f in page.frames if f.url.startswith(status.base_url+'/')]
        ohif=candidates[0] if candidates else page.wait_for_event('framenavigated',predicate=lambda f:f.url.startswith(status.base_url+'/'),timeout=60000)
        ohif.locator('input[type=file]').first.set_input_files(str(sample))
        ohif.get_by_text('gray, encode',exact=True).dblclick(timeout=60000)
        ohif.locator('canvas').first.wait_for(timeout=60000);page.wait_for_timeout(3000)
        assert 'StudyInstanceUIDs=2.25.262478289063731792084544913479622212167' in ohif.url
        capture('ohif-public-ct.png');result['public_ct_rendered_inside_theia']=True
        nav('Mission Scenario Mode');page.get_by_role('button',name='Generate scenario PDF',exact=True).click()
        page.get_by_text('Synthetic PDF generated',exact=False).wait_for(timeout=60000)
        with page.expect_download() as download:page.get_by_text('Download synthetic scenario PDF',exact=True).click()
        pdf=out/'synthetic-mission.pdf';download.value.save_as(str(pdf))
        text='\n'.join(p.extract_text() for p in PdfReader(pdf).pages)
        for expected in ['Latest: 90.000 score','HRV_RMSSD','Independent personal reference','Recorded mission context','SIMULATED_DATA','SYNTHETIC_SIMULATION_DATA']:assert expected in text,expected
        result['pdf_values_context_hrv']=True
        nav('Mission Timeline');page.get_by_role('combobox',name='Inspect recorded event',exact=True).wait_for();capture('timeline.png')
        nav('NASA Data Hub');page.get_by_text('Reproducible NASA POWER environmental reference',exact=True).click();capture('nasa-research.png')
        nav('Mission Scenario Mode');choose('Active astronaut','Mira / Workload scenario')
        page.wait_for_function("Array.from(document.querySelectorAll('.readout')).find(e=>e.textContent.includes('SYNTHETIC OBSERVATIONS'))?.querySelector('.readout-value').textContent==='150'",timeout=60000)
        assert page.locator('.readout').filter(has_text='SYNTHETIC OBSERVATIONS').locator('.readout-value').inner_text()=='150'
        choose('Active astronaut','Astra / Recovery scenario')
        page.wait_for_function("Array.from(document.querySelectorAll('.readout')).find(e=>e.textContent.includes('SYNTHETIC OBSERVATIONS'))?.querySelector('.readout-value').textContent==='250'",timeout=60000)
        assert page.locator('.readout').filter(has_text='SYNTHETIC OBSERVATIONS').locator('.readout-value').inner_text()=='250'
        result['profile_switch_isolation']=True
        visited=[]
        for name in ['Mission Overview','Scientific Analysis','Mission Scenario Mode','Health Dashboard','Health Monitoring','Data Management','Human Body Explorer','Medical Visualization Lab','NASA Data Hub','THEIA Intelligence Center','Mission Timeline','Daily Check-in','Personal Baseline','Intelligent Analysis','Nutrition','Health Guidance','Mission Reports','Settings']:
            nav(name);visited.append(name)
            if name=='Health Dashboard':capture('health-dashboard.png')
        result['pages_verified']=visited
        nav('Mission Scenario Mode');page.get_by_role('button',name='Reset synthetic scenario',exact=True).click()
        page.get_by_text('Scenario reset to the deterministic',exact=False).wait_for(timeout=60000)
        assert page.locator('.readout').filter(has_text='SYNTHETIC OBSERVATIONS').locator('.readout-value').inner_text()=='150'
        result['reset_preserves_normal_storage']=True
        nav('Mission Overview')
        orbit_frames=[f for f in page.frames if f.url.endswith('/orbit.html')]
        if orbit_frames and orbit_frames[0].get_by_role('button',name='Pause orbit',exact=True).count():orbit_frames[0].get_by_role('button',name='Pause orbit',exact=True).click()
        for width,label in [(390,'mobile'),(1024,'tablet')]:
            page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(600)
            sizes=page.locator('[data-testid=stMainBlockContainer]').evaluate('e=>[e.clientWidth,e.scrollWidth]')
            assert sizes[1]<=sizes[0]+2
            capture(label+'.png');result[label]=sizes
        page.set_viewport_size({'width':1600,'height':1800})
        page.get_by_text('Synthetic scenario workspace',exact=True).click();finish('Mission Overview')
        assert page.get_by_text('PROVENANCE /',exact=False).first.inner_text()==normal_provenance
        result['normal_provenance_unchanged']=True
        result['javascript_errors']=errors;assert not errors,errors
        (out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
        browser.close()


if __name__=='__main__':main()
