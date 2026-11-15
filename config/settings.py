from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "theia.db"
DATA_DIR = ROOT_DIR / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
REPORTS_DIR = DATA_DIR / "processed"

APP_NAME = "THEIA"
MISSION_ID = "ARCTURUS-42"
DEFAULT_ASTRONAUT_NAME = "Astra Ren"
DEFAULT_MISSION_DAY = 128

SOURCE_LABELS = {
    "REAL_SENSOR_DATA": "REAL SENSOR DATA",
    "MANUALLY_ENTERED_DATA": "MANUALLY ENTERED DATA",
    "SIMULATED_DATA": "SIMULATED DATA",
    "PUBLIC_RESEARCH_DATA": "PUBLIC RESEARCH DATA",
}

HEALTH_RULES_PATH = ROOT_DIR / "config" / "health_rules.json"
