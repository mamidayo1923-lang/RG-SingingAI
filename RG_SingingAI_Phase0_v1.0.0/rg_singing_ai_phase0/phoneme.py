from __future__ import annotations
from pathlib import Path
import json
import re

# Japanese phoneme inventory schema.
# This is intentionally conservative; G2P generation is a separate component.
PHONEME_INVENTORY = [
    "a","i","u","e","o",
    "N","Q",
    "k","ky","g","gy",
    "s","sh","z","j",
    "t","ch","ts","d",
    "n","ny",
    "h","hy","f",
    "b","by","p","py",
    "m","my",
    "r","ry",
    "w","y",
    "v",
    "cl","pau","sp","sil","AP"
]

def load_phoneme_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if "phonemes" not in data:
        raise ValueError(f"Missing 'phonemes': {path}")
    return data

def validate_phonemes(data):
    errors = []
    last = -1.0
    for i, p in enumerate(data["phonemes"]):
        ph = p.get("phoneme")
        start = p.get("start")
        end = p.get("end")
        if ph not in PHONEME_INVENTORY:
            errors.append(f"phoneme[{i}]: unknown phoneme '{ph}'")
        if not isinstance(start, (int,float)) or not isinstance(end, (int,float)):
            errors.append(f"phoneme[{i}]: invalid timestamps")
            continue
        if start < 0 or end < start:
            errors.append(f"phoneme[{i}]: invalid interval")
        if start < last:
            errors.append(f"phoneme[{i}]: non-monotonic start")
        last = start
    return errors
