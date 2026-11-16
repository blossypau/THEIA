"""Recorded events and observations, never invented physiological transitions."""
import json
from typing import Any
from database.models import MissionEvent,DailyCheckin
from database.measurements import query_measurements
from services.space_context import context_rows
from intelligence.historical import historical_analysis


def timeline_events(session,astronaut_id):
    result: list[dict[str,Any]]=[]
    for row in query_measurements(session,astronaut_id).all():
        result.append(dict(key=f'measurement:{row.id}',kind='measurement',timestamp=row.timestamp,source=row.source,
            title=f'{row.metric_name}: {row.value:g} {row.unit}',details={'measurement_id':row.id,'quality':row.data_quality_status}))
    from services.provenance import profile_provenance
    provenance={r['measurement_id']:r for r in profile_provenance(session,astronaut_id)}
    for item in result:item['details'].update(provenance[item['details']['measurement_id']])
    for row in session.query(MissionEvent).filter_by(astronaut_id=astronaut_id).all():
        result.append(dict(key=f'event:{row.id}',kind='event',timestamp=row.timestamp,
            source='SIMULATED_DATA' if session.info.get('scenario') else 'MANUALLY_ENTERED_DATA',title=row.event_type,details={'description':row.description}))
    for row in context_rows(session,astronaut_id):
        payload=json.loads(row.payload)
        result.append(dict(key=f'context:{row.id}',kind=row.kind,timestamp=row.timestamp,source=row.source,
            title=str(payload.get('environment',payload.get('metric',payload.get('origin',payload.get('state',row.kind))))),
            details={'end':str(row.end),'quality':row.quality,'instrument':row.instrument,**payload}))
    for row in session.query(DailyCheckin).filter_by(astronaut_id=astronaut_id).all():
        result.append(dict(key=f'checkin:{row.id}',kind='sleep report',timestamp=row.timestamp,
            source='SIMULATED_DATA' if session.info.get('scenario') else 'MANUALLY_ENTERED_DATA',
            title='Reported sleep duration',details={'hours':row.sleep_duration_hours,'note':'Check-in time is not inferred sleep start/end'}))
    history=historical_analysis(session,astronaut_id,persist=False)
    from datetime import datetime
    for item in history['signals']:
        for flag in item['observations']:
            if flag['flagged']:result.append(dict(key=f"historical:{flag['id']}",kind='statistical review',timestamp=datetime.fromisoformat(flag['timestamp']),
                source=item['source'],title=f"{item['metric']} historical deviation (not diagnosis)",details={'reference_ids':item['reference_ids'],**flag}))
    return sorted(result,key=lambda item:(item['timestamp'],item['key']))
