"""One pinned public codec sample; arbitrary URLs and private studies are not accepted."""
import hashlib
import io
import json
from config.settings import ROOT_DIR

MANIFEST=ROOT_DIR/'assets/testdata/ohif-gray-ct.json'


def sample_manifest():
    return json.loads(MANIFEST.read_text())


def verify_sample(content):
    info=sample_manifest()
    if len(content)!=info['bytes'] or hashlib.sha256(content).hexdigest()!=info['sha256']:
        raise ValueError('Public DICOM size/hash mismatch; sample refused')
    import pydicom
    data=pydicom.dcmread(io.BytesIO(content))
    if (data.get('PatientIdentityRemoved')!='YES' or str(data.StudyInstanceUID)!=info['study_uid']
            or str(data.PatientName)!='gray^encode^^^' or data.Rows!=512 or data.Columns!=512):
        raise ValueError('Unexpected public sample identity or geometry')
    if hashlib.sha256(data.pixel_array.astype('<i2').tobytes()).hexdigest()!=info['pixel_sha256']:
        raise ValueError('Decoded public sample pixels do not match upstream reference')
    return info


def fetch_sample():
    import requests
    info=sample_manifest()
    url=f"https://raw.githubusercontent.com/OHIF/viewer-testdata/{info['revision']}/{info['path']}"
    with requests.get(url,timeout=30,stream=True) as response:
        response.raise_for_status()
        parts=[];size=0
        for chunk in response.iter_content(65536):
            size+=len(chunk)
            if size>info['bytes']:raise ValueError('Public sample exceeds expected size')
            parts.append(chunk)
    content=b''.join(parts)
    verify_sample(content)
    return content
