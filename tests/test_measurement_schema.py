from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from utils.measurement_schema import MeasurementPayload


def test_valid_measurement_passes_expected_constraints():
    payload = {
        "metric_name": "heart_rate",
        "value": 72,
        "unit": "bpm",
        "timestamp": datetime.utcnow(),
        "source": "MANUALLY_ENTERED_DATA",
        "mission_context": "Routine check",
        "notes": "Nominal resting rate.",
    }

    validated = MeasurementPayload.model_validate(payload)

    assert validated.metric_name == "heart_rate"
    assert validated.value == 72
    assert validated.unit == "bpm"


def test_invalid_metric_name_raises_validation_error():
    payload = {
        "metric_name": "unknown_metric",
        "value": 72,
        "unit": "bpm",
        "timestamp": datetime.utcnow(),
    }

    with pytest.raises(ValidationError):
        MeasurementPayload.model_validate(payload)


def test_out_of_range_value_raises_validation_error():
    payload = {
        "metric_name": "body_temperature",
        "value": 50,
        "unit": "C",
        "timestamp": datetime.utcnow(),
    }

    with pytest.raises(ValidationError):
        MeasurementPayload.model_validate(payload)


def test_unit_mismatch_raises_validation_error():
    payload = {
        "metric_name": "oxygen_saturation",
        "value": 98,
        "unit": "bpm",
        "timestamp": datetime.utcnow(),
    }

    with pytest.raises(ValidationError):
        MeasurementPayload.model_validate(payload)
