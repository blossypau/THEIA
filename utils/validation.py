from __future__ import annotations

from datetime import datetime


def validate_timestamp(value):
    if value is None:
        return False
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_numeric(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_unit(unit: str | None, allowed_units=None):
    if unit is None:
        return False
    if allowed_units is None:
        return True
    return unit.lower() in {item.lower() for item in allowed_units}


def data_quality_flags(value, metric_name=None):
    if value is None:
        return "MISSING"
    if isinstance(value, str):
        return "INVALID"
    return "VALID"


def is_duplicate(existing_records, new_record):
    for record in existing_records:
        if record.metric_name == new_record.metric_name and record.timestamp == new_record.timestamp:
            return True
    return False
