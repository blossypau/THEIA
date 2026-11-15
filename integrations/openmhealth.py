"""Offline validation/export of pinned Open mHealth measurement bodies, not a FHIR server."""
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from jsonschema import Draft7Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4
from config.settings import ROOT_DIR
from utils.measurement_schema import MeasurementPayload

SCHEMAS=ROOT_DIR/'assets/schemas/openmhealth'
BASE='https://theia.invalid/omh/'
SUPPORTED={'heart_rate':('heart-rate','2.0','heart_rate','beats/min'),
           'body_temperature':('body-temperature','3.0','body_temperature','C'),
           'oxygen_saturation':('oxygen-saturation','2.0','oxygen_saturation','%')}
FORMATS=FormatChecker()


@FORMATS.checks('date-time', raises=(ValueError, TypeError))
def iso_datetime(value):
    # jsonschema's optional RFC3339 checker may be absent; never silently accept any string.
    if not isinstance(value,str):return True
    if 'T' not in value.upper():return False
    datetime.fromisoformat(value.replace('Z','+00:00').replace('z','+00:00'))
    return True


@lru_cache(maxsize=1)
def registry():
    resources=[(BASE+p.name,Resource.from_contents(json.loads(p.read_text()),default_specification=DRAFT4))
               for p in SCHEMAS.glob('*.json') if p.name!='manifest.json']
    return Registry().with_resources(resources)


def validate_body(metric, body):
    if metric not in SUPPORTED:raise ValueError('No verified Open mHealth mapping for this metric')
    name,version,_,_=SUPPORTED[metric]
    Draft7Validator({'$ref':BASE+f'{name}-{version}.json'},registry=registry(),format_checker=FORMATS).validate(body)
    return body


def export_measurements(frame):
    points=[];skipped=[]
    for row in frame.itertuples():
        if row.metric_name not in SUPPORTED:
            skipped.append(dict(id=int(row.id),reason='No verified mapping; scalar blood pressure lacks systolic/diastolic pair; sleep lacks session interval'))
            continue
        try:
            payload=MeasurementPayload.model_validate({k:getattr(row,k) for k in ['metric_name','value','unit','timestamp','source','data_quality_status']})
            if payload.data_quality_status!='VALID':raise ValueError('Record quality is not VALID')
            name,version,field,unit=SUPPORTED[row.metric_name]
            body={field:{'value':float(row.value),'unit':unit},'effective_time_frame':{'date_time':payload.timestamp.isoformat()+'Z'}}
            validate_body(row.metric_name,body)
            points.append(dict(schema_id=dict(namespace='omh',name=name,version=version),body=body,
                               theia_provenance=dict(measurement_id=int(row.id),source=row.source,quality=row.data_quality_status)))
        except ValueError:
            skipped.append(dict(id=int(row.id),reason='Failed THEIA validation or quality review'))
    return dict(format='THEIA bundle of Open mHealth validated bodies; not an OMH header or FHIR resource',
                schema_revision=json.loads((SCHEMAS/'manifest.json').read_text())['revision'],points=points,skipped=skipped)
