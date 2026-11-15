"""Opt-in local browser verification. Requires Playwright Chromium and a running THEIA.

Only the per-browser synthetic workspace is edited. A pinned public codec sample is
downloaded explicitly for the OHIF check; no real astronaut files are used.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from services.public_dicom import fetch_sample
from services.ohif_runtime import resolve_ohif


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8520')
    parser.add_argument('--output',default='tmp/science/browser')
    args=parser.parse_args()
    from urllib.parse import urlsplit
    url=urlsplit(args.url)
    if url.scheme!='http' or url.hostname not in {'127.0.0.1','localhost'}:
        raise ValueError('Use a local THEIA URL')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    result={};errors=[]
    with tempfile.TemporaryDirectory(prefix='theia-public-dicom-') as directory,sync_playwright() as p:
        sample=Path(directory)/'public-gray-ct.dcm';sample.write_bytes(fetch_sample())
        browser=p.chromium.launch(headless=True,args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1600,'height':1800})
        page.on('pageerror',lambda e:errors.append(str(e)))
        def finish(name):
            page.locator('.workspace-footer').filter(has_text=name).wait_for(timeout=60000)
            page.get_by_text('Stop',exact=True).wait_for(state='hidden',timeout=60000)
        def nav(name):page.get_by_text(name,exact=True).click();finish(name)
        def choose(label,value):
            page.get_by_role('combobox',name=label,exact=True).click()
            page.get_by_role('option',name=value,exact=True).click()
            page.get_by_text('Stop',exact=True).wait_for(state='hidden',timeout=60000)
        def capture(name):
            page.evaluate("document.querySelectorAll('*').forEach(e=>{if(e.scrollTop>0)e.scrollTop=0})")
            page.screenshot(path=str(out/name))
        page.goto(args.url,wait_until='networkidle');finish('Mission Overview')
        page.get_by_text('Synthetic scenario workspace',exact=True).click();finish('Mission Overview')
        nav('Scientific Analysis')
        choose('Scientific signal','heart_rate / SIMULATED_DATA')
        page.get_by_text('B − A median change:',exact=False).wait_for()
        capture('period-comparison.png');result['period_comparison']=True
        choose('Scientific tool','Open mHealth export')
        with page.expect_download() as download:
            page.get_by_text('Download validated Open mHealth bodies',exact=True).click()
        path=out/'synthetic-omh.json';download.value.save_as(str(path))
        bundle=json.loads(path.read_text())
        assert len(bundle['points'])==90 and all(x['theia_provenance']['source']=='SIMULATED_DATA' for x in bundle['points'])
        capture('openmhealth.png');result['omh_export']=True
        choose('Scientific tool','Beat-to-beat HRV')
        page.get_by_text('I confirm contiguous normal-to-normal intervals with no missing beats or untreated artifacts',exact=True).click()
        page.get_by_role('button',name='Analyze NN intervals',exact=True).click()
        page.get_by_text('Saved analysis',exact=False).wait_for(timeout=30000)
        with page.expect_download() as download:
            page.get_by_text('Download traceable HRV result',exact=True).click()
        path=out/'synthetic-hrv.json';download.value.save_as(str(path))
        hrv=json.loads(path.read_text());assert hrv['source']=='SIMULATED_DATA' and hrv['metrics']['HRV_RMSSD']>0
        capture('hrv.png');result['nn_analysis']=True
        nav('Mission Scenario Mode')
        page.get_by_role('button',name='Generate scenario PDF',exact=True).click()
        page.get_by_text('Synthetic PDF generated',exact=False).wait_for(timeout=30000)
        with page.expect_download() as download:page.get_by_text('Download synthetic scenario PDF',exact=True).click()
        path=out/'synthetic-scientific.pdf';download.value.save_as(str(path))
        text='\n'.join(p.extract_text() for p in PdfReader(path).pages)
        assert 'Source-separated longitudinal context' in text and 'Theil-Sen' in text
        result['pdf_longitudinal_section']=True
        nav('Medical Visualization Lab')
        status=resolve_ohif()
        assert status.ready,status.reason
        viewer=next(f for f in page.frames if f.url.startswith(status.base_url+'/'))
        viewer.locator('input[type=file]').first.set_input_files(str(sample))
        viewer.get_by_text('gray, encode',exact=True).dblclick(timeout=60000)
        viewer.locator('canvas').first.wait_for(timeout=60000)
        viewer.get_by_text('CT brain 512x512 16-bit signed, lossless transfer syntaxes',exact=True).first.wait_for(timeout=60000)
        page.wait_for_timeout(4000)
        assert 'StudyInstanceUIDs=2.25.262478289063731792084544913479622212167' in viewer.url
        capture('ohif-inside-theia.png');result['public_dicom_in_embedded_ohif']=True
        nav('Scientific Analysis')
        for width,label in [(390,'mobile'),(1024,'tablet')]:
            page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(500)
            sizes=page.locator('[data-testid=stMainBlockContainer]').evaluate('e=>[e.clientWidth,e.scrollWidth]')
            assert sizes[1]<=sizes[0]+2
            capture(label+'.png');result[label]=sizes
        result['javascript_errors']=errors
        assert not page.locator('[data-testid=stException]').count()
        assert not errors,errors
        (out/'results.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2),flush=True)
        browser.close()


if __name__=='__main__':main()
