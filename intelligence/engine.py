"""Single experimental analysis pipeline shared by all THEIA consumers."""
import hashlib
import json
from itertools import combinations

import numpy as np
from sklearn.ensemble import IsolationForest

from database.measurements import measurement_frame
from database.models import ScientificAnalysisRecord
from utils.measurement_schema import MeasurementPayload

VERSION = "4.1.1"
LIMITATIONS = "Experimental statistics, not a validated medical AI. Associations are not causal. Baselines include the selected period. Mixed sources are summarized separately."


def analyze(session, astronaut_id, start=None, end=None, persist=True):
    frame = measurement_frame(session, astronaut_id, start=start, end=end)
    fingerprint = hashlib.sha256((frame.to_json(date_format="iso", orient="records") + str((astronaut_id, start, end, VERSION))).encode()).hexdigest()
    source_key = f"profile:{astronaut_id}:{fingerprint}"
    cached = session.query(ScientificAnalysisRecord).filter_by(analysis_type="integrated_health", version=VERSION, dataset_source=source_key).first()
    if cached:
        return json.loads(cached.result_summary)
    result = {"version": VERSION, "astronaut_id": astronaut_id, "fingerprint": fingerprint,
              "period": {"start": str(start) if start else None, "end": str(end) if end else None},
              "parameters": {"z_threshold": 2.5, "baseline_min_samples": 5, "isolation_forest_min_samples": 20, "isolation_forest_min_unique": 5, "random_state": 42, "correlation_min_paired_days": 5}, "quality": {"total": len(frame), "excluded": 0}, "metrics": {}, "relationships": [], "limitations": LIMITATIONS}
    valid_indices = []
    for index, row in frame.iterrows():
        try:
            MeasurementPayload.model_validate({key: row[key] for key in ["metric_name", "value", "unit", "timestamp", "source", "data_quality_status"]})
            if row.data_quality_status == "VALID":
                valid_indices.append(index)
        except ValueError:
            pass
    valid = frame.loc[valid_indices].copy()
    result["quality"]["excluded"] = len(frame) - len(valid)
    result["quality"]["sources"] = frame.source.value_counts().to_dict()
    if not frame.empty:
        result["period"].update(first=frame.timestamp.min().isoformat(), last=frame.timestamp.max().isoformat())
    # Keep simulated, imported and manual/sensor cohorts distinct.
    valid["cohort"] = valid.source.map(lambda s: "simulated" if s == "SIMULATED_DATA" else "research" if s in {"PUBLIC_RESEARCH_DATA", "IMPORTED_DATA"} else "mission")
    for (metric, cohort), group in valid.groupby(["metric_name", "cohort"]):
        values = group.value.to_numpy(dtype=float)
        n = len(values)
        mean, std = float(values.mean()), float(values.std())
        elapsed = (group.timestamp - group.timestamp.min()).dt.total_seconds().to_numpy() / 86400
        slope = float(np.polyfit(elapsed, values, 1)[0]) if n >= 3 and np.ptp(elapsed) > 0 else None
        zscores = np.abs((values - mean) / std) if std > 0 else np.zeros(n)
        model = None
        if n >= 20 and std > 0 and len(np.unique(values)) >= 5:
            model = IsolationForest(random_state=42, contamination="auto").fit(values.reshape(-1,1))
        predictions = model.predict(values.reshape(-1,1)) if model is not None else np.ones(n)
        isolation_scores = model.decision_function(values.reshape(-1,1)) if model is not None else [None]*n
        anomalies = []
        for (_, row), z, prediction, isolation_score in zip(group.iterrows(), zscores, predictions, isolation_scores):
            if z <= 2.5 and prediction != -1:
                continue
            deviation = float(row.value)-mean
            methods = (["z_score"] if z>2.5 else []) + (["isolation_forest"] if prediction==-1 else [])
            anomalies.append({"id":int(row.id),"timestamp":row.timestamp.isoformat(),"value":float(row.value),"unit":row.unit,
                "z_score":float(z),"methods":methods,"baseline_mean":mean,"baseline_std":std,"deviation":deviation,
                "samples":n,"input_cohort":f"{metric}:{cohort}","source":row.source,"quality":row.data_quality_status,
                "isolation_decision_score":float(isolation_score) if isolation_score is not None else None,
                "explanation":f"Observed {float(row.value):.3f} {row.unit}; {abs(deviation):.3f} {row.unit} {'above' if deviation>=0 else 'below'} the selected-period mean. Absolute z-score {float(z):.3f}. This is a statistical pattern, not a diagnosis.",
                "limitations":"Reference includes this observation. Unsupervised flags depend on available samples and parameters; no clinical risk probability is estimated."})
        key = f"{metric}:{cohort}"
        result["metrics"][key] = {"metric": metric, "cohort": cohort, "measurement_ids": [int(value) for value in group.id], "samples": n, "unit": group.unit.iloc[0],
            "mean": mean, "median": float(np.median(values)), "std": std, "min": float(values.min()), "max": float(values.max()),
            "slope_per_day": slope, "recent_change": float(values[-1] - values[-2]) if n > 1 else None,
            "latest": float(values[-1]), "latest_timestamp": group.timestamp.iloc[-1].isoformat(),
            "status": "sufficient" if n >= 5 else "insufficient_data", "isolation_forest_status": "evaluated" if n >= 20 and std > 0 and len(np.unique(values)) >= 5 else "insufficient_or_low_variability",
            "anomalies": anomalies, "sources": group.source.value_counts().to_dict(),
            "explanation": "Absolute z-score > 2.5; Isolation Forest evaluated from 20 samples with at least 5 distinct values. Flags indicate statistical outliers only."}
    if not valid.empty:
        valid["day"] = valid.timestamp.dt.floor("D")
        for cohort, group in valid.groupby("cohort"):
            daily = group.pivot_table(index="day", columns="metric_name", values="value", aggfunc="mean")
            for left, right in combinations(daily.columns, 2):
                paired = daily[[left, right]].dropna()
                if len(paired) >= 5 and (paired.std() > 0).all():
                    result["relationships"].append({"left": left, "right": right, "cohort": cohort, "paired_days": len(paired),
                        "pearson_r": float(paired[left].corr(paired[right])), "alignment": "UTC daily mean; exploratory, not causal"})
    if persist:
        session.add(ScientificAnalysisRecord(analysis_type="integrated_health", model_name="THEIA statistical engine", version=VERSION,
            input_variables=",".join(sorted(valid.metric_name.unique())), result_summary=json.dumps(result, allow_nan=False),
            dataset_source=source_key, limitations=LIMITATIONS))
        session.commit()
    return result
