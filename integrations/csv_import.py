from __future__ import annotations

import csv
from datetime import datetime

from sqlalchemy.orm import Session

from database.models import HealthMeasurement


def import_csv(session: Session, csv_path: str, astronaut_id: int = 1):
    with open(csv_path, newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)
        added = []
        for row in rows:
            measurement = HealthMeasurement(
                astronaut_id=astronaut_id,
                metric_name=row["metric_name"],
                value=float(row["value"]),
                unit=row["unit"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                source=row.get("source", "PUBLIC_RESEARCH_DATA"),
                data_quality_status=row.get("data_quality_status", "VALID"),
                mission_context=row.get("mission_context"),
            )
            session.add(measurement)
            added.append(measurement)
        session.commit()
    return added
