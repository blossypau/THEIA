from __future__ import annotations


def normalize_metric_name(metric_name: str) -> str:
    return metric_name.strip().lower().replace(" ", "_")


def convert_to_celsius(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit in {"c", "celsius", "°c"}:
        return float(value)
    if unit in {"f", "fahrenheit", "°f"}:
        return (float(value) - 32) * 5 / 9
    return float(value)


def normalize_blood_pressure(value: float, unit: str | None = None) -> float:
    if unit and unit.lower() in {"kpa"}:
        return value / 0.133322
    return float(value)
