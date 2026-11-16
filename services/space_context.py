"""Typed contextual observations. No hazard values are inferred from physiology."""
from datetime import datetime,timedelta
import hashlib
import json
import math
from collections import defaultdict
from pydantic import BaseModel,ConfigDict,Field,model_validator
from database.models import SpaceObservation
from database.measurements import measurement_frame

GRAVITY={'Earth':(9.80665,'Conventional standard g, not a local measurement'),
         'Orbital microgravity':(None,'Apparent weightlessness during free fall, not zero gravitational field'),
         'Moon':(1.62,'Approximate surface gravity'), 'Mars':(3.73,'Mean surface gravity, NASA fact sheet')}
GRAVITY_SOURCES=['https://www.nist.gov/pml/special-publication-811','https://science.nasa.gov/moon/facts/',
                 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html']
C_KM_S=299792.458
HAZARDS={
 'Altered Gravity Fields':dict(kinds=['gravity','activity'],metrics=['heart_rate','fatigue'],url='https://www.nasa.gov/humans-in-space/the-human-body-in-space/',
    note='Gravity transitions motivate research on muscles, bones, balance, fluid shifts and cardiovascular adaptation. This atlas and pulse/fatigue records do not measure bone loss, atrophy or neuroocular changes.'),
 'Space Radiation':dict(kinds=['radiation'],metrics=[],url='https://www.nasa.gov/hrp/hazard-space-radiation/',
    note='GCR, solar particle events and trapped radiation are distinct contexts. Only recorded dosimetry is analyzed; no individual cancer risk, operational alert threshold or Gy-to-Sv conversion is inferred.'),
 'Isolation and Confinement':dict(kinds=['wellbeing','activity'],metrics=['sleep_hours','fatigue','energy','mood'],url='https://www.nasa.gov/hrp/hazard-isolation-and-confinement/',
    note='Sleep, workload and voluntary self-reports provide descriptive context, not psychological diagnosis. No camera/voice inference or cognitive diagnosis is performed.'),
 'Distance from Earth':dict(kinds=['communications'],metrics=[],url='https://www.nasa.gov/hrp/hazards/',
    note='Light-travel time is an ideal geometric calculation. It is not network latency, link availability or a connection to a spacecraft. Local mirror synchronization is an explicitly simulated test.'),
 'Hostile/Closed Environments':dict(kinds=['environment'],metrics=['sleep_hours','fatigue','heart_rate'],url='https://www.nasa.gov/hrp/hazard-hostile-closed-environments/',
    note='Recorded temperature, humidity, pressure, CO2, light and noise can be explored alongside physiology. Associations are not causal; symptoms cannot infer environmental concentrations.')}
ENV_UNITS={'co2':'ppm','temperature':'C','humidity':'%','pressure':'kPa','light':'lux','noise':'dBA'}
DOSE_UNITS={'Gy':('absorbed',1),'mGy':('absorbed',.001),'uGy':('absorbed',.000001),
            'Sv':('equivalent',1),'mSv':('equivalent',.001),'uSv':('equivalent',.000001)}


class ContextPayload(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: str
    timestamp: datetime
    end: datetime | None = None
    source: str = 'MANUALLY_ENTERED_DATA'
    quality: str = 'VALID'
    instrument: str = Field(min_length=1,max_length=200)
    payload: dict

    @model_validator(mode='after')
    def validate_context(self):
        from utils.measurement_schema import MeasurementPayload
        self.timestamp=MeasurementPayload.validate_time(self.timestamp)
        if self.end is not None:
            self.end=MeasurementPayload.validate_time(self.end)
            if self.end<=self.timestamp:raise ValueError('End must follow start')
        if self.source not in {'MANUALLY_ENTERED_DATA','IMPORTED_DATA','SIMULATED_DATA','PUBLIC_RESEARCH_DATA','REAL_SENSOR_DATA'}:raise ValueError('Unknown context source')
        if self.quality not in {'VALID','REVIEW','INVALID'}:raise ValueError('Unknown quality')
        p=self.payload
        def finite(name,minimum=None):
            value=p.get(name)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or (minimum is not None and value<minimum):raise ValueError(f'Invalid {name}')
        if self.kind=='gravity':
            if p.get('environment') not in GRAVITY or not str(p.get('phase','')).strip():raise ValueError('Gravity requires a known environment and phase')
        elif self.kind=='environment':
            metric=p.get('metric')
            if metric not in ENV_UNITS or p.get('unit')!=ENV_UNITS[metric]:raise ValueError('Environmental metric/unit mismatch')
            finite('value',None if metric=='noise' else -273.15 if metric=='temperature' else 0)
            if metric=='humidity' and p['value']>100:raise ValueError('Humidity exceeds 100%')
            if 'sampling_seconds' in p:finite('sampling_seconds',.001)
        elif self.kind=='radiation':
            unit=p.get('unit','');rate=unit.endswith('/h');baseunit=unit[:-2] if rate else unit
            if baseunit not in DOSE_UNITS or p.get('basis')!=DOSE_UNITS[baseunit][0]:raise ValueError('Radiation basis/unit mismatch; Gy and Sv cannot be interchanged')
            if p.get('origin') not in {'GCR','SPE','TRAPPED','UNKNOWN'}:raise ValueError('Unknown radiation origin')
            quantity=p.get('quantity')
            if quantity not in {'dose_increment','dose_rate','cumulative_reading'} or (quantity=='dose_rate')!=rate:raise ValueError('Dose quantity/unit mismatch')
            finite('value',0)
            if p.get('uncertainty') is not None:finite('uncertainty',0)
            if quantity!='cumulative_reading' and self.end is None:raise ValueError('Dose rates and increments require an exposure interval')
        elif self.kind=='communications':
            if p.get('state') not in {'CONNECTED','DELAYED','OFFLINE','SYNC PENDING'}:raise ValueError('Unknown link state')
            if p.get('distance_km') is not None:finite('distance_km',0)
            if p.get('simulated_link') is not True:raise ValueError('No real spacecraft link connector exists; mark operational communication scenarios simulated')
        elif self.kind in {'wellbeing','activity'}:
            finite('value',0)
            if p.get('metric') not in {'stress_score','workload_score','social_minutes','activity_minutes','sleep_start_hour','sleep_end_hour'}:raise ValueError('Unknown voluntary contextual metric')
            if p['metric'].endswith('score') and p['value']>100:raise ValueError('Self-report scores use 0-100')
            if p['metric'].endswith('hour') and p['value']>=24:raise ValueError('UTC clock hours must be 0 <= value < 24')
            if p['metric']=='social_minutes' and p.get('consent') is not True:raise ValueError('Social logging requires explicit voluntary consent')
        else:raise ValueError('Unknown mission context kind')
        json.dumps(p,allow_nan=False)
        return self


def add_context(session,astronaut_id,data,commit=True):
    item=ContextPayload.model_validate(data)
    from database.models import AstronautProfile
    if session.get(AstronautProfile,astronaut_id) is None:raise ValueError('Unknown mission profile')
    if session.info.get('scenario') and item.source!='SIMULATED_DATA':raise ValueError('Synthetic workspace rejects non-synthetic context')
    if item.source=='REAL_SENSOR_DATA' and not session.info.get('verified_sensor_capture'):raise ValueError('No verified context sensor capture')
    canonical=json.dumps(item.model_dump(),default=str,sort_keys=True)
    identity=hashlib.sha256(f'{astronaut_id}:{canonical}'.encode()).hexdigest()
    row=session.query(SpaceObservation).filter_by(identity_key=identity).first()
    if row:return row
    row=SpaceObservation(astronaut_id=astronaut_id,identity_key=identity,kind=item.kind,timestamp=item.timestamp,end=item.end,
        source=item.source,quality=item.quality,instrument=item.instrument,payload=json.dumps(item.payload,allow_nan=False))
    session.add(row)
    if commit:session.commit()
    else:session.flush()
    return row


def context_rows(session,astronaut_id,kind=None):
    query=session.query(SpaceObservation).filter_by(astronaut_id=astronaut_id)
    if kind:query=query.filter_by(kind=kind)
    return query.order_by(SpaceObservation.timestamp,SpaceObservation.id).all()


def context_frame(session,astronaut_id,kind=None):
    import pandas as pd
    return pd.DataFrame([{'id':r.id,'kind':r.kind,'timestamp':r.timestamp,'end':r.end,'source':r.source,'quality':r.quality,'instrument':r.instrument,**json.loads(r.payload)} for r in context_rows(session,astronaut_id,kind)])


def radiation_summary(rows):
    groups=defaultdict(list)
    for row in rows:
        if row.quality!='VALID':continue
        p=json.loads(row.payload)
        groups[(row.source,row.instrument,p['basis'],p['origin'])].append((row,p))
    result=[]
    for (source,instrument,basis,origin),items in groups.items():
        intervals=[];counters=[]
        for row,p in items:
            unit=p['unit'].removesuffix('/h');value=p['value']*DOSE_UNITS[unit][1]
            if p['quantity']=='cumulative_reading':counters.append((row.timestamp,value));continue
            if p['quantity']=='dose_rate':value*=(row.end-row.timestamp).total_seconds()/3600
            intervals.append((row.timestamp,row.end,value))
        intervals.sort();overlap=any(b[0]<a[1] for a,b in zip(intervals,intervals[1:]))
        counters.sort();reset=any(b[1]<a[1] or (b[0]==a[0] and b[1]!=a[1]) for a,b in zip(counters,counters[1:]))
        recorded_hours=sum((i[1]-i[0]).total_seconds()/3600 for i in intervals) if not overlap else None
        window_hours=(max(i[1] for i in intervals)-min(i[0] for i in intervals)).total_seconds()/3600 if intervals else None
        result.append(dict(source=source,instrument=instrument,basis=basis,origin=origin,unit='Gy' if basis=='absorbed' else 'Sv',
            interval_sum=None if overlap or not intervals else sum(i[2] for i in intervals),overlap=overlap,
            cumulative_change=counters[-1][1]-counters[0][1] if len(counters)>=2 and not reset else None,counter_reset_or_inconsistent=reset,
            recorded_hours=recorded_hours,window_hours=window_hours,interval_coverage=recorded_hours/window_hours if recorded_hours is not None and window_hours else None,
            samples=len(items),note='No cross-instrument/origin/source sum; cumulative readings are differenced, never summed. Unknown uncertainties are not replaced by zero.'))
    return result


def propagation_seconds(distance_km):
    if not math.isfinite(distance_km) or distance_km<0:raise ValueError('Distance must be finite and nonnegative')
    return distance_km/C_KM_S


def hazard_inventory(session,astronaut_id):
    frame=measurement_frame(session,astronaut_id);rows=context_rows(session,astronaut_id)
    return {name:dict(**definition,context_records=sum(r.kind in definition['kinds'] for r in rows),
        available_metrics=[m for m in definition['metrics'] if m in frame.metric_name.values],
        recorded_sources=sorted({r.source for r in rows if r.kind in definition['kinds']})) for name,definition in HAZARDS.items()}


def observation_readiness(session,astronaut_id):
    frame=measurement_frame(session,astronaut_id);rows=context_rows(session,astronaut_id)
    domains={
        'Cardiovascular':(['heart_rate','blood_pressure','oxygen_saturation'],[],'Scalar pressure is not a systolic/diastolic pair; no clinical forecast.'),
        'Sleep / recovery':(['sleep_hours','fatigue','energy'],[],'Reported duration only; no sleep stages or validated recovery score.'),
        'Musculoskeletal activity':([],['activity'],'Recorded activity is not bone density, strength or muscle-loss measurement.'),
        'Wellbeing':(['mood'],['wellbeing'],'Voluntary self-reports, not psychological diagnosis.'),
        'Cognitive performance':([],[],'No compatible cognitive measurements or diagnostic inference.'),
        'Environment':([],['environment'],'Only recorded concentrations/conditions; no inferred safety thresholds.'),
        'Gravity context':([],['gravity'],'Reference environment, not measured biological adaptation.'),
        'Documented radiation':([],['radiation'],'Dosimetry quantities remain separate; no personal risk score.')}
    result=[]
    for name,(metrics,kinds,note) in domains.items():
        physiology=frame[frame.metric_name.isin(metrics)]
        context=[r for r in rows if r.kind in kinds]
        count=len(physiology)+len(context)
        result.append(dict(area=name,status='RECORDED DATA' if count else 'NO DATA',observations=count,
            indicators=', '.join(sorted(physiology.metric_name.unique())),sources=', '.join(sorted(set(physiology.source)|{r.source for r in context})),
            quality='Declared schema/quality labels; not clinical verification',limitations=note))
    return result


def demo_context(session,astronaut_id,day):
    if not session.info.get('scenario'):raise ValueError('Mission demonstration requires isolated synthetic storage')
    from database.models import AstronautProfile
    session.get(AstronautProfile,astronaut_id).mission_day=31+day
    start=datetime(2026,1,31,8)+timedelta(days=day);end=start+timedelta(hours=1)
    environment='Earth' if day<3 else 'Orbital microgravity' if day<12 else 'Moon' if day<17 else 'Mars'
    common=dict(timestamp=start,end=end,source='SIMULATED_DATA',quality='VALID',instrument='Deterministic software scenario; no real sensor')
    records=[dict(kind='gravity',payload={'environment':environment,'phase':'Reference' if day<12 else 'Surface simulation','activity':'Synthetic exercise log'}),
        dict(kind='environment',payload={'metric':'co2','value':700+day%5*20,'unit':'ppm','sampling_seconds':86400}),
        dict(kind='environment',payload={'metric':'temperature','value':22+day%3*.1,'unit':'C','sampling_seconds':86400}),
        dict(kind='environment',payload={'metric':'humidity','value':45+day%4,'unit':'%','sampling_seconds':86400}),
        dict(kind='environment',payload={'metric':'pressure','value':101.3,'unit':'kPa','sampling_seconds':86400}),
        dict(kind='radiation',payload={'origin':'SPE' if day==12 else 'GCR','basis':'absorbed','quantity':'dose_increment','value':.01 if day==12 else .001,'unit':'mGy','uncertainty':None}),
        dict(kind='wellbeing',payload={'metric':'workload_score','value':40+day%5}),
        dict(kind='activity',payload={'metric':'activity_minutes','value':30+day%4}),
        dict(kind='communications',payload={'state':'OFFLINE' if day%4==0 else 'DELAYED','simulated_link':True,'distance_km':384400 if environment=='Moon' else 225000000 if environment=='Mars' else 400})]
    for record in records:add_context(session,astronaut_id,{**common,**record},commit=False)
    session.commit()


def phase_comparison(session,astronaut_id,metric='heart_rate'):
    frame=measurement_frame(session,astronaut_id,metric);result=[]
    from intelligence.engine import analyze
    valid_ids={i for item in analyze(session,astronaut_id,persist=False)['metrics'].values() for i in item['measurement_ids']}
    frame=frame[frame.id.isin(valid_ids)]
    for row in context_rows(session,astronaut_id,'gravity'):
        if row.quality!='VALID' or row.end is None:continue
        p=json.loads(row.payload)
        subset=frame[(frame.timestamp>=row.timestamp)&(frame.timestamp<(row.end or row.timestamp))]
        for (source,provenance),group in subset.groupby(['source','provenance_class']):
            result.append(dict(phase=p['phase'],environment=p['environment'],context_source=row.source,measurement_source=source,
                provenance_class=provenance,start=row.timestamp.isoformat(),end=row.end.isoformat() if row.end else None,samples=len(group),median=float(group.value.median()),unit=group.unit.iloc[0]))
    return result


def environment_associations(session,astronaut_id):
    import pandas as pd
    environment=context_frame(session,astronaut_id,'environment')
    physiology=measurement_frame(session,astronaut_id)
    if environment.empty or physiology.empty:return []
    environment=environment[environment.quality=='VALID'].copy()
    physiology=physiology[physiology.data_quality_status=='VALID'].copy()
    environment['day']=pd.to_datetime(environment.timestamp).dt.floor('D')
    physiology['day']=physiology.timestamp.dt.floor('D')
    result=[]
    for (metric,source,instrument),group in environment.groupby(['metric','source','instrument']):
        left=group.groupby('day').value.mean()
        for target,observations in physiology[physiology.source==source].groupby('metric_name'):
            right=observations.groupby('day').value.mean()
            paired=pd.concat([left.rename('environment'),right.rename('physiology')],axis=1,sort=True).dropna()
            if len(paired)>=5 and (paired.std()>0).all():
                result.append(dict(environment=metric,physiology=target,source=source,instrument=instrument,paired_days=len(paired),
                    pearson_r=float(paired.environment.corr(paired.physiology)),method='Same-source UTC daily means; exploratory, not causal or adjusted for confounding/multiple comparisons'))
    return result


def import_context_csv(session,astronaut_id,content,kind):
    import io
    import pandas as pd
    if len(content)>10*1024*1024:raise ValueError('Context CSV exceeds 10 MB')
    if kind not in {'radiation','environment','gravity'}:raise ValueError('Unsupported context import')
    frame=pd.read_csv(io.BytesIO(content))
    if not 1<=len(frame)<=10000:raise ValueError('Context import requires 1-10000 rows')
    items=[]
    for _,row in frame.iterrows():
        values={k:v for k,v in row.to_dict().items() if pd.notna(v)}
        timestamp=values.pop('timestamp',None);end=values.pop('end',None)
        instrument=values.pop('instrument','Imported context file; source declared')
        quality=values.pop('quality','VALID');declared=values.pop('source',None)
        if declared=='SIMULATED_DATA':raise ValueError('Synthetic context cannot be imported into normal storage')
        items.append(ContextPayload.model_validate(dict(kind=kind,timestamp=timestamp,end=end,instrument=instrument,quality=quality,source='IMPORTED_DATA',payload=values)))
    try:
        rows=[add_context(session,astronaut_id,item.model_dump(),commit=False) for item in items]
        session.commit();return rows
    except Exception:session.rollback();raise
