from __future__ import annotations

import numpy as np


def rule_based_flagging(values):
    if len(values) < 3:
        return []
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std(ddof=0)) or 1.0
    flags = []
    for value in values:
        z = abs((float(value) - mean) / std)
        if z > 2.5:
            flags.append({"flag_level": "potentially_important_change", "score": float(z), "explanation": "Value exceeds normal personal variability."})
    return flags
