from __future__ import annotations

import json
from pathlib import Path


def evaluate_demo_model(metrics):
    metrics = metrics or {"accuracy": 0.0, "f1": 0.0}
    output = {"model_name": "IsolationForest_demo", "metrics": metrics, "timestamp": "2026-11-14T00:00:00Z"}
    path = Path("data/models") / "evaluation_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output
