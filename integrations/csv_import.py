"""Atomic, validated CSV measurement import."""
import pandas as pd
import io
import hashlib
from database.measurements import insert_measurement
from utils.measurement_schema import MeasurementPayload


def import_csv(session, csv_path, astronaut_id=1):
    if session.info.get('scenario'):
        raise ValueError('CSV import is disabled in the exclusively synthetic scenario workspace')
    from pathlib import Path
    content=Path(csv_path).read_bytes() if isinstance(csv_path,(str,Path)) else csv_path.getvalue() if hasattr(csv_path,'getvalue') else csv_path.read()
    if isinstance(content,str):content=content.encode('utf-8')
    if len(content)>20*1024*1024:raise ValueError('CSV exceeds 20 MB')
    frame = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
    required = {"metric_name", "value", "unit", "timestamp"}
    if not required.issubset(frame.columns) or frame.empty or len(frame) > 100000:
        raise ValueError("CSV requires metric_name, value, unit, timestamp and 1-100000 rows")
    payloads = []
    for index, (_,row) in enumerate(frame.iterrows(),start=2):
        data = {key: value for key, value in row.to_dict().items() if key in MeasurementPayload.model_fields and pd.notna(value)}
        if data.get('source')=='SIMULATED_DATA':raise ValueError('Synthetic CSV cannot be imported into normal storage; use an isolated scenario')
        data["source"] = "IMPORTED_DATA"
        try:
            payloads.append(MeasurementPayload.model_validate(data))
        except ValueError as exc:
            raise ValueError(f"CSV row {index}: {exc}") from exc
    try:
        from integrations.acquisition import Batch,ingest
        from database.models import HealthMeasurement
        digest=hashlib.sha256(content).hexdigest()
        filename=Path(csv_path).name if isinstance(csv_path,(str,Path)) else str(getattr(csv_path,'name',None) or 'Explicit CSV upload')
        result=ingest(session,astronaut_id,Batch('uploaded-csv',filename,
            [p.model_dump() for p in payloads],'IMPORTED_DATA',digest))
        return [session.get(HealthMeasurement,record_id) for record_id in result['measurement_ids']]
    except Exception:
        session.rollback()
        raise
