from __future__ import annotations

from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALLOWED_METRICS = {
    "heart_rate",
    "blood_pressure",
    "blood_glucose",
    "body_temperature",
    "sleep_hours",
    "mood",
    "energy",
    "fatigue",
    "oxygen_saturation",
}

ALLOWED_UNITS = {
    "bpm",
    "mmHg",
    "mg/dL",
    "C",
    "hours",
    "score",
    "%",
}

UNIT_BY_METRIC = {
    "heart_rate": {"bpm"},
    "blood_pressure": {"mmHg"},
    "blood_glucose": {"mg/dL"},
    "body_temperature": {"C"},
    "sleep_hours": {"hours"},
    "mood": {"score"},
    "energy": {"score"},
    "fatigue": {"score"},
    "oxygen_saturation": {"%"},
}

METRIC_RANGES = {
    "heart_rate": (30, 220),
    "blood_pressure": (40, 250),
    "blood_glucose": (30, 400),
    "body_temperature": (30, 45),
    "sleep_hours": (0, 24),
    "mood": (0, 100),
    "energy": (0, 100),
    "fatigue": (0, 100),
    "oxygen_saturation": (40, 100),
}

ALLOWED_SOURCES = {
    "MANUAL_INPUT",
    "IMPORTED_DATA",
    "REAL_SENSOR_DATA",
    "MANUALLY_ENTERED_DATA",
    "SIMULATED_DATA",
    "PUBLIC_RESEARCH_DATA",
}


class MeasurementPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(..., min_length=2, max_length=80)
    value: float = Field(..., ge=0, allow_inf_nan=False)
    unit: str = Field(..., min_length=1, max_length=20)
    timestamp: datetime
    source: str = "MANUALLY_ENTERED_DATA"
    data_quality_status: str = "VALID"
    mission_context: str | None = None
    notes: str | None = None

    @field_validator("timestamp")
    @classmethod
    def validate_time(cls, value: datetime) -> datetime:
        value = value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
        if value > datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5):
            raise ValueError("Timestamp cannot be in the future; use UTC")
        return value

    @field_validator("metric_name")
    @classmethod
    def validate_metric_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_METRICS:
            raise ValueError(f"Unsupported metric_name '{value}'. Allowed metrics: {sorted(ALLOWED_METRICS)}")
        return normalized

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in ALLOWED_UNITS:
            raise ValueError(f"Unsupported unit '{value}'. Allowed units: {sorted(ALLOWED_UNITS)}")
        return normalized

    @field_validator("mission_context")
    @classmethod
    def validate_mission_context(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > 120:
            raise ValueError("mission_context must be 120 characters or less")
        return trimmed

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > 500:
            raise ValueError("notes must be 500 characters or less")
        return trimmed

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALLOWED_SOURCES:
            raise ValueError(f"Unsupported source '{value}'. Allowed sources: {sorted(ALLOWED_SOURCES)}")
        return normalized

    @field_validator("data_quality_status")
    @classmethod
    def validate_quality(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"VALID", "REVIEW", "MISSING", "INVALID"}:
            raise ValueError("data_quality_status must be VALID, REVIEW, MISSING, or INVALID")
        return normalized

    @model_validator(mode="after")
    def validate_metric_unit_and_range(self) -> "MeasurementPayload":
        metric = self.metric_name
        unit = self.unit
        allowed_units = UNIT_BY_METRIC.get(metric, {unit})
        if unit not in allowed_units:
            raise ValueError(f"Metric '{metric}' must use one of {sorted(allowed_units)}")

        lower_bound, upper_bound = METRIC_RANGES[metric]
        if not lower_bound <= float(self.value) <= upper_bound:
            raise ValueError(
                f"Metric '{metric}' must be between {lower_bound} and {upper_bound} {unit}"
            )
        return self
