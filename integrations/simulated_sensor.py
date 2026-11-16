from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone


def generate_simulated_measurement(metric_name: str):
    baselines = {
        "heart_rate": (60, 90),
        "blood_pressure": (100, 135),
        "blood_glucose": (90, 120),
        "body_temperature": (36.5, 37.2),
        "sleep_hours": (5.5, 8.5),
        "mood": (50, 90),
        "energy": (50, 90),
        "fatigue": (10, 70),
    }
    low, high = baselines.get(metric_name, (0, 100))
    value = round(random.uniform(low, high), 2)
    return {
        "metric_name": metric_name,
        "value": value,
        "unit": {
            "heart_rate": "bpm",
            "blood_pressure": "mmHg",
            "blood_glucose": "mg/dL",
            "body_temperature": "C",
            "sleep_hours": "hours",
            "mood": "score",
            "energy": "score",
            "fatigue": "score",
        }.get(metric_name, "score"),
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(5, 180))).isoformat(),
        "source": "SIMULATED_DATA",
        "data_quality_status": "VALID",
    }


def simulated_sensor_stream():
    return [
        generate_simulated_measurement(name)
        for name in ["heart_rate", "blood_pressure", "blood_glucose", "body_temperature", "sleep_hours", "mood"]
    ]
