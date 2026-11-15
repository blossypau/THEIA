"""Reproducible NASA POWER Earth-environment reference, never spacecraft measurements."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from config.settings import ROOT_DIR

PARAMETERS={'T2M':('temperature','C'),'RH2M':('humidity','%'),'PS':('pressure','kPa')}
REQUEST={'parameters':'T2M,RH2M,PS','community':'RE','latitude':28.5721,'longitude':-80.648,
         'start':'20240101','end':'20240107','format':'JSON','time-standard':'UTC'}
URL='https://power.larc.nasa.gov/api/temporal/daily/point'


def parse_power(data):
    if data['header']['time_standard']!='UTC':raise ValueError('POWER reference must use UTC')
    fill=data['header']['fill_value'];rows=[]
    for parameter,(metric,unit) in PARAMETERS.items():
        if data['parameters'][parameter]['units']!=unit:raise ValueError('Unexpected POWER units')
        for day,value in data['properties']['parameter'][parameter].items():
            if value==fill:continue
            if not isinstance(value,(float,int)) or not __import__('math').isfinite(value):raise ValueError('Invalid POWER value')
            rows.append({'timestamp':pd.to_datetime(day,format='%Y%m%d').isoformat(),'metric':metric,'value':value,'unit':unit,
                'source':'PUBLIC_RESEARCH_DATA','context':'Terrestrial gridded model near Kennedy Space Center, not cabin or personal sensor'})
    if not rows:raise ValueError('No valid POWER observations')
    return pd.DataFrame(rows)


def load_reference():
    path=ROOT_DIR/'assets/research/nasa-power-ksc-20240101-07.json'
    manifest=json.loads(path.with_suffix('.manifest.json').read_text())
    content=path.read_bytes()
    if hashlib.sha256(content).hexdigest()!=manifest['sha256']:raise ValueError('NASA reference checksum mismatch')
    return parse_power(json.loads(content)),manifest


def fetch_power(session):
    import requests
    if session.info.get('scenario'):raise ValueError('Public observations are not synthetic; switch to normal research workspace')
    response=requests.get(URL,params=REQUEST,timeout=30);response.raise_for_status()
    if len(response.content)>2*1024*1024:raise ValueError('NASA response exceeds 2 MB')
    frame=parse_power(response.json())
    from services.datasets import register_table
    record,_=register_table(session,frame.to_csv(index=False).encode(),'NASA-POWER-Earth-reference.csv',response.url,'NASA-POWER-KSC-20240101-07')
    return record,frame
