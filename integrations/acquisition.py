"""Explicit connectors -> atomic validation -> provenance -> SQLite."""
from dataclasses import dataclass
from datetime import datetime,timedelta
import hashlib
import io
import json
from pathlib import Path
import pandas as pd
from database.models import AcquisitionReceipt
from database.measurements import insert_measurement
from utils.measurement_schema import MeasurementPayload


@dataclass
class Batch:
    connector: str
    instrument: str
    records: list
    source: str
    identity: str
    capture_verified: bool = False


def ingest(session, astronaut_id, batch):
    if session.info.get('scenario') and batch.source!='SIMULATED_DATA':raise ValueError('Only synthetic acquisition is permitted in this workspace')
    if batch.source=='SIMULATED_DATA' and not session.info.get('scenario'):
        raise ValueError('Automatic simulation requires isolated scenario storage')
    if batch.source=='REAL_SENSOR_DATA' and not batch.capture_verified:raise ValueError('No active verified device capture')
    if not batch.records:raise ValueError('Connector returned no records')
    identity=hashlib.sha256(f'{astronaut_id}:{batch.connector}:{batch.identity}'.encode()).hexdigest()
    existing=session.get(AcquisitionReceipt,identity)
    if existing:return json.loads(existing.details)
    payloads=[MeasurementPayload.model_validate(dict(r,source=batch.source)) for r in batch.records]
    previous=session.info.copy()
    try:
        session.info['verified_sensor_capture']=batch.capture_verified
        session.info['acquisition_provenance']={'connector':batch.connector,'instrument':batch.instrument,'receipt':identity}
        ids=[insert_measurement(session,astronaut_id,p,commit=False).id for p in payloads]
        result={'status':'STORED','receipt':identity,'measurement_ids':ids,'source':batch.source,'connector':batch.connector,'capture_verified':batch.capture_verified}
        session.add(AcquisitionReceipt(id=identity,astronaut_id=astronaut_id,connector=batch.connector,status='STORED',details=json.dumps(result)))
        session.flush()
        if session.info.get('scenario'):
            from database.models import TestOutbox
            session.add(TestOutbox(id=identity,astronaut_id=astronaut_id,payload=json.dumps([p.model_dump() for p in payloads],default=str)))
        session.commit();return result
    except Exception:
        session.rollback();raise
    finally:
        session.info.clear();session.info.update(previous)


def record_error(session,astronaut_id,connector,message):
    from uuid import uuid4
    session.rollback()
    session.add(AcquisitionReceipt(id=str(uuid4()),astronaut_id=astronaut_id,connector=connector,status='ERROR',details=json.dumps({'error':str(message)[:800]})))
    session.commit()


class SyntheticConnector:
    def __init__(self,scenario='Long mission'):
        self.scenario=scenario;self.position=0;self.state='STOPPED';self.speed=1
    def command(self,action):
        if action=='reset':self.position=0;self.state='STOPPED'
        elif action in {'start','resume'}:self.state='RUNNING'
        elif action=='pause':self.state='PAUSED'
        elif action=='stop':self.state='STOPPED'
        else:raise ValueError('Unknown replay command')
    def poll(self):
        if self.state!='RUNNING':return []
        result=[]
        for _ in range(min(int(self.speed),10)):
            if self.position>=20:self.state='COMPLETED';break
            day=self.position;offset=6 if self.scenario=='Workload example' else 0
            values={'heart_rate':(66+day%4+offset+(22 if day>=12 else 0),'bpm'),
                    'sleep_hours':(7.3-(day%3)*.1-(1.4 if day>=12 else 0),'hours'),
                    'fatigue':(25+day%5+(35 if day>=12 else 0),'score'),'energy':(75-day%6,'score'),'mood':(72-day%4,'score')}
            if day==19:
                values.update(heart_rate=(130,'bpm'),fatigue=(90,'score'),sleep_hours=(3,'hours'))
            timestamp=datetime(2026,1,31,8)+timedelta(days=day)
            records=[dict(metric_name=m,value=v,unit=u,timestamp=timestamp) for m,(v,u) in values.items()]
            result.append(Batch('synthetic-replay',self.scenario,records,'SIMULATED_DATA',f'{self.scenario}:{day}'))
            self.position+=1
        return result


class FolderConnector:
    """Authorized directory only. Stable, newline-terminated CSV; no symlinks, recursion or moves."""
    def __init__(self,directory):
        self.directory=Path(directory).expanduser().resolve(strict=True)
        if not self.directory.is_dir():raise ValueError('Authorized path must be a directory')
        self.seen={};self.done=set()
    def poll(self):
        batches=[]
        for path in sorted(self.directory.glob('*.csv')):
            if path.is_symlink() or path.resolve().parent!=self.directory:continue
            stat=path.stat();signature=(stat.st_size,stat.st_mtime_ns)
            if stat.st_size>20*1024*1024:raise ValueError('Automatic CSV exceeds 20 MB')
            if self.seen.get(path.name)!=signature:self.seen[path.name]=signature;continue
            data=path.read_bytes()
            after=path.stat()
            if (after.st_size,after.st_mtime_ns)!=signature or not data.endswith((b'\n',b'\r')):continue
            digest=hashlib.sha256(data).hexdigest()
            if digest in self.done:continue
            frame=pd.read_csv(io.BytesIO(data))
            if not 1<=len(frame)<=100000:raise ValueError('CSV requires 1-100000 rows')
            required={'metric_name','value','unit','timestamp'}
            if not required.issubset(frame.columns):raise ValueError('Automatic CSV requires metric_name,value,unit,timestamp')
            columns=list(required|({'data_quality_status','mission_context','notes'}&set(frame.columns)))
            batches.append(Batch('authorized-folder',str(self.directory),frame[columns].to_dict('records'),'IMPORTED_DATA',digest))
        return batches
    def acknowledge(self,batch):self.done.add(batch.identity)


class APIConnector:
    def __init__(self,url,token_env=None):
        from urllib.parse import urlsplit
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.username or parsed.password or parsed.fragment:raise ValueError('Authorized API requires HTTPS without embedded credentials')
        self.url=url;self.token_env=token_env
    def poll(self):
        import os,requests
        headers={}
        if self.token_env:
            token=os.environ.get(self.token_env)
            if not token:raise ValueError('API token environment variable is missing')
            headers['Authorization']='Bearer '+token
        with requests.get(self.url,headers=headers,timeout=5,allow_redirects=False,stream=True) as response:
            response.raise_for_status()
            if response.status_code!=200:raise ValueError('API requires HTTP 200, without redirects')
            data=b''
            for chunk in response.iter_content(65536):
                data+=chunk
                if len(data)>1024*1024:raise ValueError('API response exceeds 1 MB')
        rows=json.loads(data)
        if not isinstance(rows,list) or not 1<=len(rows)<=1000:raise ValueError('API requires 1-1000 measurement objects')
        return [Batch('authorized-api',__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(self.url)._replace(query='').geturl(),rows,'IMPORTED_DATA',hashlib.sha256(data).hexdigest())]
