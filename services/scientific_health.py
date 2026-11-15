"""Source-separated, descriptive longitudinal analysis of validated scalar observations."""
import hashlib
import json
from typing import Any, TypedDict
import numpy as np
import pandas as pd
from scipy.stats import theilslopes
from database.measurements import measurement_frame
from database.models import ScientificAnalysisRecord
from intelligence.engine import analyze

VERSION = '1.0.0'


class PeriodSummary(TypedDict):
    days: int
    requested_days: int
    median: float | None


LIMITATIONS = ('Descriptive research only, not diagnosis or a prospective forecast. Daily means reduce sampling-frequency weighting; '
               'missing days are not imputed. Sources remain separate. Period differences do not establish causation. '
               'Sleep duration is reported duration, not sleep staging, efficiency or a validated recovery score.')


def longitudinal_analysis(session, astronaut_id, periods=None, persist=True, start=None, end=None):
    base = analyze(session, astronaut_id, start=start, end=end, persist=persist)
    frame = measurement_frame(session, astronaut_id, start=start, end=end)
    ids = {i for item in base['metrics'].values() for i in item['measurement_ids']}
    frame = frame[frame.id.isin(ids)].copy()
    normalized = None
    if periods is not None:
        if len(periods) != 2 or any(len(p) != 2 for p in periods):
            raise ValueError('Select start and end for both periods')
        normalized = [[pd.Timestamp(d).date().isoformat() for d in p] for p in periods]
        a, b = normalized
        if a[0] > a[1] or b[0] > b[1] or not (a[1] < b[0] or b[1] < a[0]):
            raise ValueError('Periods must be ordered within each range and must not overlap')
    fingerprint = hashlib.sha256(json.dumps([VERSION, base['fingerprint'], normalized]).encode()).hexdigest()
    key = f'profile:{astronaut_id}:{fingerprint}'
    cached = session.query(ScientificAnalysisRecord).filter_by(analysis_type='longitudinal_health', version=VERSION, dataset_source=key).first()
    if cached:
        return json.loads(cached.result_summary)
    result: dict[str, Any] = dict(version=VERSION, astronaut_id=astronaut_id, fingerprint=fingerprint,
                  engine_snapshot=base['fingerprint'], periods=normalized, quality=base['quality'],
                  method='UTC daily means; median/IQR; Theil-Sen median pairwise slope',
                  signals=[], limitations=LIMITATIONS)
    if not frame.empty:
        frame['day'] = frame.timestamp.dt.floor('D')
        for (metric, source), group in frame.groupby(['metric_name', 'source']):
            daily = group.groupby('day').value.mean().sort_index()
            x = (daily.index - daily.index.min()).days.to_numpy(dtype=float)
            y = daily.to_numpy(dtype=float)
            # Bound the quadratic pairwise estimator for very long records, disclose any subsampling.
            indexes = np.unique(np.linspace(0, len(y)-1, min(len(y), 1000), dtype=int))
            slope = float(theilslopes(y[indexes], x[indexes]).slope) if len(y) >= 5 else None
            days_span = int((daily.index.max()-daily.index.min()).days)+1
            item = dict(metric=metric, source=source, unit=group.unit.iloc[0], observations=len(group),
                        measurement_ids=[int(i) for i in group.id], days=len(daily), span_days=days_span,
                        observed_day_fraction=len(daily)/days_span, median=float(np.median(y)),
                        iqr=float(np.percentile(y,75)-np.percentile(y,25)), latest=float(y[-1]),
                        theil_sen_per_day=slope, trend_days_used=len(indexes),
                        daily=[dict(day=d.isoformat(), value=float(v)) for d,v in daily.items()],
                        status='sufficient_for_descriptive_trend' if len(y)>=5 else 'insufficient_days')
            if normalized:
                parts: list[PeriodSummary]=[]
                for start,end in normalized:
                    values=daily.loc[start:end]
                    parts.append(dict(days=len(values), requested_days=int((pd.Timestamp(end)-pd.Timestamp(start)).days)+1,
                                      median=float(values.median()) if len(values) else None))
                enough=all(p['days']>=5 for p in parts)
                a_median,b_median=parts[0]['median'],parts[1]['median']
                delta=b_median-a_median if enough and a_median is not None and b_median is not None else None
                item['comparison']=dict(a=parts[0],b=parts[1],status='descriptive_only' if enough else 'insufficient_days',
                                        median_change=delta, percent_change=100*delta/a_median if delta is not None and a_median is not None and a_median!=0 else None)
            result['signals'].append(item)
    if persist:
        session.add(ScientificAnalysisRecord(analysis_type='longitudinal_health', model_name='THEIA daily descriptive analysis',
            version=VERSION,input_variables=','.join(sorted(frame.metric_name.unique())),result_summary=json.dumps(result,allow_nan=False),
            dataset_source=key,limitations=LIMITATIONS))
        session.commit()
    return result
