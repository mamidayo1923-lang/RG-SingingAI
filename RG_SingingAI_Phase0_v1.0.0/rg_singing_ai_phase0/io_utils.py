from __future__ import annotations
from pathlib import Path
import json
import numpy as np

def ensure_dirs(dataset: Path) -> None:
    dirs = [
        "raw/audio", "raw/recording_metadata",
        "reference/midi", "reference/lyrics",
        "annotations/phoneme", "annotations/note", "annotations/alignment",
        "features/f0", "features/energy", "features/voicing",
        "features/mel", "features/spectral_envelope", "features/hnr",
        "features/formants", "features/aperiodicity",
        "features/breathiness", "features/voice_quality",
        "manifests", "qc", "logs"
    ]
    for d in dirs:
        (dataset / d).mkdir(parents=True, exist_ok=True)

def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8"
    )

def save_npy(path: Path, arr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, np.asarray(arr, dtype=np.float32), allow_pickle=False)
