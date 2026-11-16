"""Install the pinned MIT OHIF browser runtime without Node or private files."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent.parent


def install(destination=None):
    target=Path(destination or ROOT/'third_party/OHIF-Viewers/platform/app/dist').resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Runtime destination must stay inside this project')
    if (target/'index.html').is_file() and (target/'app.js').is_file():
        print('Existing OHIF build preserved.');return target
    manifest=json.loads((ROOT/'config/ohif-runtime.json').read_text(encoding='utf-8'))
    with urllib.request.urlopen(manifest['url'],timeout=60) as response:content=response.read(manifest['bytes']+1)
    if len(content)!=manifest['bytes'] or hashlib.sha256(content).hexdigest()!=manifest['sha256']:
        raise ValueError('OHIF archive size/checksum mismatch; installation refused')
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for item in archive.infolist():
            resolved=(target/item.filename).resolve()
            if not resolved.is_relative_to(target) or (item.external_attr>>16)&0o170000==0o120000:
                raise ValueError('Unsafe runtime archive path')
        if not {'index.html','app.js','LICENSE'}.issubset(archive.namelist()):raise ValueError('Incomplete runtime archive')
        target.mkdir(parents=True,exist_ok=True);archive.extractall(target)
    print('Verified OHIF browser runtime installed. No DICOM studies included.')
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination')
    args=parser.parse_args();install(args.destination)


if __name__=='__main__':main()
