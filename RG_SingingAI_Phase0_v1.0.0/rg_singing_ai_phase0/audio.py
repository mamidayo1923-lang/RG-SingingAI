from __future__ import annotations
from pathlib import Path
import numpy as np
import soundfile as sf

class AudioError(RuntimeError):
    pass

def read_audio(path: Path, target_sr: int = 44100):
    info = sf.info(path)
    if info.format.upper() != "WAV":
        raise AudioError(f"Not WAV: {path}")
    if info.subtype.upper() not in {"PCM_16", "PCM_24", "PCM_32"}:
        raise AudioError(f"Unsupported PCM subtype: {info.subtype}")

    y, sr = sf.read(path, always_2d=False, dtype="float32")
    if y.ndim == 2:
        y = np.mean(y, axis=1, dtype=np.float32)

    # Phase 0 standard is 44.1kHz. Do not silently resample.
    if sr != target_sr:
        raise AudioError(
            f"Sample rate mismatch: {sr} Hz; expected {target_sr} Hz. "
            "Create a compliant recording or explicitly preprocess it."
        )

    return y.astype(np.float32, copy=False), sr, info

def audio_qc(y: np.ndarray, cfg):
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    rms = float(np.sqrt(np.mean(np.square(y)))) if len(y) else 0.0
    rms_dbfs = 20.0 * np.log10(max(rms, 1e-12))
    dc = float(np.mean(y)) if len(y) else 0.0
    return {
        "samples": int(len(y)),
        "duration_sec": float(len(y) / cfg.sample_rate),
        "peak_abs": peak,
        "clipping_detected": bool(peak >= cfg.clipping_threshold),
        "rms_dbfs": rms_dbfs,
        "silence_like": bool(rms_dbfs <= cfg.silence_rms_dbfs),
        "dc_offset": dc,
        "dc_offset_exceeds_limit": bool(abs(dc) > cfg.dc_offset_abs_max),
        "finite": bool(np.isfinite(y).all()),
    }
