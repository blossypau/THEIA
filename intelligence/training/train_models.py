from __future__ import annotations

import json
from pathlib import Path

from sklearn.ensemble import IsolationForest


def train_demo_model(feature_matrix):
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(feature_matrix)
    model_path = Path("data/models") / "isolation_forest_demo.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps({"model": "IsolationForest", "notes": "Experimental demonstration only"}), encoding="utf-8")
    return model
