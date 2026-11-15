"""Limited MIT-licensed NeuroKit time-domain adaptation; no full-package/DLL import."""
import hashlib
import io
import json
import numpy as np
import pandas as pd
from database.models import ScientificAnalysisRecord


def synthetic_nn():
    """Deterministic artificial intervals, not a simulated sensor acquisition."""
    t=np.arange(400)
    return 800+35*np.sin(2*np.pi*t/6)+12*np.sin(2*np.pi*t/45)


def read_nn_csv(content):
    if len(content)>1024*1024:
        raise ValueError('NN CSV must be at most 1 MB')
    frame=pd.read_csv(io.BytesIO(content))
    if list(frame.columns)!=['nn_ms']:
        raise ValueError('CSV must contain exactly one column: nn_ms, contiguous normal-to-normal intervals in milliseconds')
    return pd.to_numeric(frame.nn_ms,errors='raise').to_numpy(dtype=float)


def read_nn_recording(content):
    if len(content)>1024*1024:raise ValueError('NN CSV exceeds 1 MB')
    frame=pd.read_csv(io.BytesIO(content))
    if 'nn_ms' not in frame or not set(frame.columns).issubset({'nn_ms','end_time_s','artifact'}):
        raise ValueError('Use nn_ms, optionally end_time_s and artifact (0/1). No daily bpm data.')
    options={}
    if 'end_time_s' in frame:options['end_time_s']=pd.to_numeric(frame.end_time_s,errors='raise').to_numpy()
    if 'artifact' in frame:options['artifact_flags']=pd.to_numeric(frame.artifact,errors='raise').to_numpy()
    return pd.to_numeric(frame.nn_ms,errors='raise').to_numpy(),options


def analyze_nn(intervals, source, confirmed_nn=False, end_time_s=None, artifact_flags=None, unit='ms'):
    if source not in {'SIMULATED_DATA','IMPORTED_DATA'}:
        raise ValueError('NN source must be explicitly SIMULATED_DATA or IMPORTED_DATA')
    if not confirmed_nn:
        raise ValueError('Confirm contiguous normal-to-normal intervals; ectopic beats and gaps require upstream review')
    if unit!='ms':raise ValueError('NN intervals must be supplied in milliseconds')
    values=np.asarray(intervals,dtype=float)
    if values.ndim!=1 or not 120<=len(values)<=20000 or not np.isfinite(values).all():
        raise ValueError('Provide 120-20000 finite contiguous NN intervals')
    if (values<200).any() or (values>3000).any() or values.sum()<120000:
        raise ValueError('Intervals must be 200-3000 ms and cover at least 120 seconds; no samples are silently dropped')
    if artifact_flags is not None:
        flags=np.asarray(artifact_flags)
        if flags.shape!=values.shape or not np.isin(flags,[0,1]).all() or flags.any():raise ValueError('Marked artifacts require upstream review; no automatic removal is performed')
    if end_time_s is not None:
        times=np.asarray(end_time_s,dtype=float)
        if times.shape!=values.shape or not np.isfinite(times).all() or not np.allclose(np.diff(times),values[1:]/1000,atol=.001,rtol=0):
            raise ValueError('Noncontiguous or invalid NN timestamps; differences must match successive intervals within 1 ms')
    # Adapted from NeuroKit2 0.3.0 hrv/hrv_time.py (MIT); see assets/licenses/neurokit2.
    # Upstream pNN50 divides by N intervals, not N-1 differences. Preserve and disclose that convention.
    differences=np.diff(values)
    selected={'HRV_MeanNN':float(np.mean(values)), 'HRV_SDNN':float(np.std(values,ddof=1)),
              'HRV_RMSSD':float(np.sqrt(np.mean(differences**2))),
              'HRV_pNN50':float(np.sum(np.abs(differences)>50)/len(values)*100)}
    if not all(np.isfinite(v) for v in selected.values()):
        raise ValueError('This interval series does not produce finite time-domain statistics')
    digest=hashlib.sha256(values.astype('<f8').tobytes()).hexdigest()
    return dict(method='THEIA NumPy subset of NeuroKit2 time-domain formulas',library_version='theia-nn-1.0.0',reference_version='NeuroKit2 0.3.0',pnn50_denominator='N intervals (NeuroKit convention)',source=source,sha256=digest,
                intervals=len(values),duration_seconds=float(values.sum()/1000),metrics=selected,nn_ms=values.tolist(),
                quality='Timestamp continuity checked; user-attested NN classification' if end_time_s is not None else 'User-attested continuity; cannot independently verify missing beats without timestamps or ECG',
                end_time_s=np.asarray(end_time_s).tolist() if end_time_s is not None else None,
                artifact_flags=np.asarray(artifact_flags).tolist() if artifact_flags is not None else None,
                limitations='Time-domain exploratory HRV only. No diagnosis, sleep staging or recovery score. No automatic artifact correction. '
                'Recording length, posture, activity and preprocessing affect comparability. No HRV is computed from daily bpm values.')


def save_nn_analysis(session, astronaut_id, result):
    if session.info.get('scenario') and result['source']!='SIMULATED_DATA':
        raise ValueError('Imported physiological signals are not permitted in the synthetic workspace')
    from database.models import AstronautProfile
    if session.get(AstronautProfile,astronaut_id) is None:
        raise ValueError('Unknown astronaut')
    key=f"profile:{astronaut_id}:{result['source']}:{result['sha256']}"
    row=session.query(ScientificAnalysisRecord).filter_by(analysis_type='nn_time_domain',version=result['library_version'],dataset_source=key).first()
    if row is None:
        row=ScientificAnalysisRecord(analysis_type='nn_time_domain',model_name='THEIA NumPy subset / NeuroKit2 temporal formulas',version=result['library_version'],
            input_variables='contiguous NN intervals (ms)',result_summary=json.dumps(result,allow_nan=False),dataset_source=key,limitations=result['limitations'])
        session.add(row);session.commit()
    return row
