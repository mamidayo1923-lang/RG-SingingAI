from __future__ import annotations
import numpy as np

def feature_qc(features, cfg):
    report = {}
    f0 = features.get("f0")
    if f0 is not None and len(f0):
        invalid = ~np.isfinite(f0) | (f0 <= 0)
        report["f0_invalid_ratio"] = float(np.mean(invalid))
        report["f0_valid_ratio"] = 1.0 - report["f0_invalid_ratio"]
        report["f0_exceeds_invalid_limit"] = bool(
            report["f0_invalid_ratio"] > cfg.max_invalid_f0_ratio
        )

    for name, arr in features.items():
        a = np.asarray(arr)
        report[f"{name}_finite"] = bool(np.isfinite(a).all()) if a.size else True
        report[f"{name}_shape"] = list(a.shape)
    return report
