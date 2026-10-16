"""Optional high-resolution acoustic analysis using WORLD when installed.

WORLD's algorithms are established analysis methods, but output is not 'calibrated'
without microphone/room calibration and validation against labeled reference data.
"""
from __future__ import annotations
import numpy as np


def analyze_world(wav_path: str, *, frame_period_ms: float = 5.0) -> dict:
    try:
        import soundfile as sf
        import pyworld as pw
    except ImportError as e:
        raise RuntimeError("Install optional dependencies: pip install pyworld soundfile") from e
    x, sr = sf.read(wav_path, dtype="float64", always_2d=True)
    if x.shape[1] != 1:
        raise ValueError("Input must be mono; downmix explicitly before analysis")
    if sr < 16000 or not np.isfinite(x).all() or len(x) < sr // 4:
        raise ValueError("Audio must be finite mono audio, >=16 kHz, and at least 0.25 s")
    x = x[:, 0]
    f0, t = pw.harvest(x, sr, f0_floor=55.0, f0_ceil=1100.0, frame_period=frame_period_ms)
    f0 = pw.stonemask(x, f0, t, sr)
    sp = pw.cheaptrick(x, f0, t, sr)
    ap = pw.d4c(x, f0, t, sr)
    # HNR derived from periodic vs aperiodic spectral energy; a WORLD-based estimate,
    # not a certified calibrated measurement. Avoid claiming precision beyond validation.
    eps = 1e-12
    p = np.sum(sp, axis=1) + eps
    a = np.sum(ap * sp, axis=1) + eps
    hnr_db = 10.0 * np.log10(np.maximum(p - np.minimum(a, p), eps) / np.minimum(a, p))
    # LPC formants are highly sensitive to vocal tract model, sample rate and order.
    # Report spectral-envelope peaks as candidates, not definitive anatomical formants.
    formants = []
    freqs = np.arange(sp.shape[1]) * (sr / 2) / max(1, sp.shape[1] - 1)
    for row in sp:
        smooth = np.convolve(row, np.ones(5)/5, mode="same")
        peaks = np.where((smooth[1:-1] > smooth[:-2]) & (smooth[1:-1] >= smooth[2:]))[0] + 1
        peaks = [int(k) for k in peaks if 200 <= freqs[k] <= 5000]
        peaks.sort(key=lambda k: smooth[k], reverse=True)
        chosen = sorted(float(freqs[k]) for k in peaks[:5])
        formants.append((chosen + [0.0]*5)[:5])
    return {"time_s":t.astype(np.float32), "f0_hz":f0.astype(np.float32),
            "hnr_db_estimate":hnr_db.astype(np.float32), "spectral_envelope":sp.astype(np.float32),
            "aperiodicity":ap.astype(np.float32), "formant_candidates_hz":np.asarray(formants,dtype=np.float32),
            "metadata":{"algorithm":"WORLD Harvest + StoneMask + CheapTrick + D4C",
                        "limitations":"Not calibrated; validate against reference annotations and recording-chain calibration."}}
