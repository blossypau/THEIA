"""Personal references strictly before the evaluated observations, separated by source."""
import hashlib
import json
from typing import Any
import pandas as pd
from database.measurements import measurement_frame
from database.models import ScientificAnalysisRecord
from intelligence.engine import analyze


def historical_analysis(session, astronaut_id, start=None, end=None, persist=True):
    frame=measurement_frame(session,astronaut_id,end=end)
    base=analyze(session,astronaut_id,end=end,persist=False)
    valid_ids={i for item in base['metrics'].values() for i in item['measurement_ids']}
    frame=frame[frame.id.isin(valid_ids)].copy()
    fingerprint=hashlib.sha256((base['fingerprint']+str((start,end,'historical-1'))).encode()).hexdigest()
    key=f'profile:{astronaut_id}:{fingerprint}'
    cached=session.query(ScientificAnalysisRecord).filter_by(analysis_type='historical_reference',dataset_source=key).first()
    if cached:return json.loads(cached.result_summary)
    result: dict[str,Any]=dict(fingerprint=fingerprint,astronaut_id=astronaut_id,signals=[],parameters={'minimum_observed_days':5,'minimum_samples':5,'descriptive_z_threshold':2.5},
        limitations='Reference excludes evaluated observations. Deviations are not diagnoses. Sources are separate; calibration and activity may differ.')
    for (metric,source),group in frame.groupby(['metric_name','source']):
        cutoff=pd.Timestamp(start) if start is not None else group.timestamp.max()
        if cutoff.tzinfo is not None:cutoff=cutoff.tz_convert('UTC').tz_localize(None)
        reference=group[group.timestamp<cutoff];evaluated=group[group.timestamp>=cutoff]
        days=reference.timestamp.dt.floor('D').nunique() if len(reference) else 0
        enough=len(reference)>=5 and days>=5
        mean=float(reference.value.mean()) if len(reference) else None
        median=float(reference.value.median()) if len(reference) else None
        std=float(reference.value.std(ddof=0)) if len(reference) else None
        span=(reference.timestamp.max().date()-reference.timestamp.min().date()).days+1 if len(reference) else 0
        observations=[]
        for row in evaluated.itertuples():
            delta=float(row.value)-mean if enough and mean is not None else None
            z=delta/std if delta is not None and std is not None and std>0 else None
            flagged=bool(abs(z)>2.5) if z is not None else bool(enough and std==0 and delta!=0)
            observations.append(dict(id=int(row.id),timestamp=row.timestamp.isoformat(),value=float(row.value),delta=delta,z_score=z,flagged=flagged))
        result['signals'].append(dict(metric=metric,source=source,unit=group.unit.iloc[0],reference_before=cutoff.isoformat(),
            reference_ids=[int(i) for i in reference.id],samples=len(reference),days=int(days),span_days=span,
            coverage=float(days/span) if span else 0,mean=mean,median=median,std=std,
            iqr=float(reference.value.quantile(.75)-reference.value.quantile(.25)) if len(reference) else None,
            status='sufficient' if enough else 'insufficient_history',observations=observations,
            method='Prior exact-source mean/SD; signed z-score beyond +/-2.5. Zero-SD change has no infinite score.'))
    if persist:
        session.add(ScientificAnalysisRecord(analysis_type='historical_reference',model_name='Independent historical reference',version='1',
            input_variables=','.join(sorted(frame.metric_name.unique())),result_summary=json.dumps(result,allow_nan=False),dataset_source=key,limitations=result['limitations']))
        session.commit()
    return result
