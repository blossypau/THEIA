"""Real GLB mesh identifiers and educational system associations."""
import json
import struct
from functools import lru_cache
from config.settings import ROOT_DIR
from intelligence.engine import analyze
from services.analysis_views import metric_view

MODEL_PATH = ROOT_DIR / "assets/anatomy/body.glb"

@lru_cache(maxsize=1)
def structure_registry():
    if not MODEL_PATH.exists():
        return {}
    with MODEL_PATH.open("rb") as handle:
        header = handle.read(12)
        if header[:4] != b"glTF":
            raise ValueError("Invalid anatomical GLB")
        size, chunk = struct.unpack("<II", handle.read(8))
        model = json.loads(handle.read(size))
    return {node["name"]: node.get("extras", {}) for node in model.get("nodes", []) if "mesh" in node and node.get("name")}


def structure_system(identifier):
    name = identifier.lower()
    for terms, system in [(("heart", "aorta", "arter", "vein"), "Cardiovascular"), (("lung", "trachea"), "Respiratory"), (("brain", "cerebell", "spinal cord"), "Nervous"), (("stomach", "liver", "intestin"), "Digestive"), (("kidney", "bladder"), "Urinary")]:
        if any(term in name for term in terms):
            return system
    return "Musculoskeletal"

SYSTEM_METRICS = {"Cardiovascular": ["heart_rate", "blood_pressure"], "Respiratory": ["oxygen_saturation"],
    "Nervous": ["sleep_hours", "mood", "fatigue"], "Digestive": ["blood_glucose"], "Urinary": [], "Musculoskeletal": ["fatigue", "sleep_hours"]}


def anatomy_view(session, astronaut_id, identifier):
    registry = structure_registry()
    if identifier not in registry:
        raise ValueError("Structure identifier is not present in the loaded GLB")
    system = structure_system(identifier)
    return {"identifier": identifier, "system": system, "metadata": registry[identifier],
            "metrics": {metric: metric_view(session, astronaut_id, metric) for metric in SYSTEM_METRICS[system]},
            "analysis": analyze(session, astronaut_id)}
