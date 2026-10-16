"""P1/P2 diagnostic acoustic feature extraction.

These interpretable descriptors are not ground truth and are not a singing
synthesis model. Feature arrays use frame-start timestamps (no centered padding).
"""
from pathlib import Path
import numpy as np
import soundfile as sf

FEATURE_CONFIG = {
    "feature_schema_version": "2.1.0",
    "sample_rate": 44100,
    "n_fft": 2048,
    "hop_length": 256,
    "n_mels": 80,
    "f0_min_hz": 65.0,
    "f0_max_hz": 1000.0,
    "window": "hann_periodic_false",
    "mel_scale": "htk",
    "log_floor": 1e-10,
    "f0_method": "fft_autocorrelation_diagnostic",
    "frame_time_convention": "frame_start_seconds",
}


def _hz_to_mel(hz):
    return 2595.0 * np.log10(1.0 + np.asarray(hz, dtype=np.float64) / 700.0)


def _mel_to_hz(mel):
    return 700.0 * (10.0 ** (np.asarray(mel, dtype=np.float64) / 2595.0) - 1.0)


def _mel_filter(sr, n_fft, n_mels):
    if n_mels < 1:
        raise ValueError("n_mels must be >= 1")
    hz = _mel_to_hz(np.linspace(_hz_to_mel(0), _hz_to_mel(sr / 2), n_mels + 2))
    bins = np.floor((n_fft + 1) * hz / sr).astype(int)
    filt = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(1, n_mels + 1):
        left, center, right = (int(v) for v in bins[m - 1:m + 2])
        center = max(center, left + 1)
        right = max(right, center + 1)
        left0, center0, right0 = max(0, left), min(center, filt.shape[1]), min(right, filt.shape[1])
        if center0 > left0:
            k = np.arange(left0, center0)
            filt[m - 1, k] = (k - left) / max(1, center - left)
        if right0 > max(0, center):
            k = np.arange(max(0, center), right0)
            filt[m - 1, k] = (right - k) / max(1, right - center)
    # Degenerate filters at the highest bins are not useful; ensure no negative weights.
    np.maximum(filt, 0, out=filt)
    return filt


def _read_mono_wav(path, cfg):
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Audio file not found: {p}")
    audio, sr = sf.read(str(p), dtype="float32", always_2d=True)
    if audio.size == 0 or len(audio) == 0:
        raise ValueError("Audio is empty")
    if sr != int(cfg["sample_rate"]):
        raise ValueError(f"Expected {cfg['sample_rate']} Hz, got {sr}; resample explicitly before extraction")
    if audio.shape[1] != 1:
        raise ValueError(f"Expected mono audio, got {audio.shape[1]} channels")
    if not np.isfinite(audio).all():
        raise ValueError("Audio contains NaN or infinite samples")
    return audio[:, 0], sr


def _frame_audio(x, n_fft, hop):
    if n_fft < 16:
        raise ValueError("n_fft must be >= 16")
    if hop < 1 or hop > n_fft:
        raise ValueError("hop_length must be in [1, n_fft]")
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    return np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop]


def _autocorrelation_fft(frames):
    """Linear autocorrelation via FFT, normalized per frame; O(N log N)."""
    y = frames.astype(np.float64, copy=True)
    y -= y.mean(axis=1, keepdims=True)
    n = y.shape[1]
    n_fft = 1 << (2 * n - 1).bit_length()
    spectrum = np.fft.rfft(y, n=n_fft, axis=1)
    ac = np.fft.irfft(spectrum * np.conjugate(spectrum), n=n_fft, axis=1)[:, :n]
    zero = ac[:, :1]
    ac = ac / np.maximum(zero, 1e-18)
    return ac, np.sqrt(np.mean(y * y, axis=1))


def _estimate_f0(frames, sr, cfg):
    ac, rms = _autocorrelation_fft(frames)
    f0 = np.zeros(len(frames), dtype=np.float32)
    confidence = np.zeros(len(frames), dtype=np.float32)
    lo = max(1, int(np.floor(sr / float(cfg["f0_max_hz"]))))
    hi = min(frames.shape[1] - 2, int(np.ceil(sr / float(cfg["f0_min_hz"]))))
    if hi <= lo:
        raise ValueError("F0 range is incompatible with n_fft/sample rate")
    for i in range(len(frames)):
        if rms[i] < 1e-5:
            continue
        segment = ac[i, lo:hi + 1]
        lag_idx = int(np.argmax(segment))
        lag = lo + lag_idx
        # Parabolic interpolation reduces integer-lag quantization. Clamp correction.
        if 0 < lag < ac.shape[1] - 1:
            a, b, c = ac[i, lag - 1], ac[i, lag], ac[i, lag + 1]
            denom = a - 2.0 * b + c
            delta = 0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0
            lag_f = lag + float(np.clip(delta, -0.5, 0.5))
        else:
            lag_f = float(lag)
        conf = float(np.clip(ac[i, lag], 0.0, 1.0))
        confidence[i] = conf
        if conf >= 0.35 and lag_f > 0:
            value = sr / lag_f
            if float(cfg["f0_min_hz"]) <= value <= float(cfg["f0_max_hz"]):
                f0[i] = value
    return f0, confidence, rms.astype(np.float32)


def extract_baseline_features(path, config=None):
    cfg = dict(FEATURE_CONFIG)
    cfg.update(config or {})
    x, sr = _read_mono_wav(path, cfg)
    n_fft, hop = int(cfg["n_fft"]), int(cfg["hop_length"])
    frames = _frame_audio(x, n_fft, hop)
    window = np.hanning(n_fft).astype(np.float32)
    spec = np.abs(np.fft.rfft(frames * window[None, :], axis=1)).astype(np.float32)
    power = spec * spec
    mel_filter = _mel_filter(sr, n_fft, int(cfg["n_mels"]))
    mel = power @ mel_filter.T
    log_mel = np.log(np.maximum(mel, float(cfg["log_floor"]))).astype(np.float32)
    f0, f0_confidence, frame_rms = _estimate_f0(frames, sr, cfg)
    frame_times = (np.arange(len(frames), dtype=np.float64) * hop / sr).astype(np.float32)
    return {
        "config": cfg,
        "sample_rate": int(sr),
        "duration_sec": float(len(x) / sr),
        "frame_times_sec": frame_times,
        "frame_rms": frame_rms,
        "log_mel": log_mel,
        "f0_hz": f0,
        "f0_confidence_proxy": f0_confidence,
        "feature_note": "Diagnostic baseline only. F0 confidence is an autocorrelation proxy; validate against trusted labels.",
    }


def _spectral_descriptors(frames, sr, n_fft, f0_hz=None):
    """Return interpretable descriptors; HNR/formants remain uncalibrated proxies."""
    win = np.hanning(n_fft).astype(np.float32)
    mag = np.abs(np.fft.rfft(frames * win[None, :], axis=1)).astype(np.float32)
    power = mag * mag
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    # Cepstral low-pass smoothing gives a more defensible broad envelope than a 9-bin average.
    log_mag = np.log(np.maximum(mag, 1e-10))
    cep = np.fft.irfft(log_mag, n=n_fft, axis=1).real
    cutoff = max(1, min(80, n_fft // 8))
    liftered = np.zeros_like(cep)
    liftered[:, :cutoff + 1] = cep[:, :cutoff + 1]
    liftered[:, -cutoff + 1:] = cep[:, -cutoff + 1:]
    envelope = np.exp(np.fft.rfft(liftered, n=n_fft, axis=1).real[:, :n_fft // 2 + 1]).astype(np.float32)
    # Spectral flatness and >4 kHz power fraction are descriptors, not direct measures of voice quality.
    flat = np.exp(np.mean(np.log(power + 1e-12), axis=1)) / (np.mean(power, axis=1) + 1e-12)
    high_band = freqs >= 4000
    high_ratio = ((power[:, high_band].sum(axis=1) + 1e-12) / (power.sum(axis=1) + 1e-12)
                  if np.any(high_band) else np.zeros(len(frames)))
    ac, rms = _autocorrelation_fft(frames)
    hnr = np.zeros(len(frames), dtype=np.float32)
    formants = np.zeros((len(frames), 3), dtype=np.float32)
    formant_conf = np.zeros((len(frames), 3), dtype=np.float32)
    for i in range(len(frames)):
        if rms[i] < 1e-5:
            continue
        minlag = max(1, int(sr / 1000))
        maxlag = min(frames.shape[1] - 2, int(sr / 60))
        if maxlag > minlag:
            periodic = float(np.clip(np.max(ac[i, minlag:maxlag + 1]), 0.0, 0.9999))
            hnr[i] = 10.0 * np.log10((periodic + 1e-8) / (1.0 - periodic + 1e-8))
        row = envelope[i].copy()
        row[(freqs < 250) | (freqs > 5000)] = 0
        peaks = np.where((row[1:-1] > row[:-2]) & (row[1:-1] >= row[2:]))[0] + 1
        peaks = sorted((int(k) for k in peaks), key=lambda k: row[k], reverse=True)
        selected = []
        for k in peaks:
            hz = float(freqs[k])
            if all(abs(hz - old_hz[0]) >= 250 for old_hz in selected):
                selected.append((hz, float(row[k])))
            if len(selected) == 3:
                break
        selected.sort(key=lambda pair: pair[0])
        for j, (hz, amp) in enumerate(selected):
            formants[i, j] = hz
            formant_conf[i, j] = amp / (float(np.max(row)) + 1e-12)
    return {
        "spectral_envelope": np.log(np.maximum(envelope, 1e-10)).astype(np.float32),
        "hnr_db_proxy": hnr,
        "formants_hz_estimate": formants,
        "formant_peak_strength_proxy": formant_conf,
        "aperiodicity_proxy": np.clip(flat, 0, 1).astype(np.float32),
        "breathiness_proxy": np.clip(high_ratio, 0, 1).astype(np.float32),
        "voice_quality_proxy": np.stack([hnr, np.clip(flat, 0, 1), np.clip(high_ratio, 0, 1)], axis=1).astype(np.float32),
    }


def extract_p2_features(path, config=None):
    """Extract P1 features plus P2 descriptors, with consistent framing and finite outputs."""
    base = extract_baseline_features(path, config)
    cfg = base["config"]
    x, sr = _read_mono_wav(path, cfg)
    frames = _frame_audio(x, int(cfg["n_fft"]), int(cfg["hop_length"]))
    base.update(_spectral_descriptors(frames, sr, int(cfg["n_fft"]), base["f0_hz"]))
    base["config"] = dict(cfg, feature_schema_version="2.1.0", p2_descriptors=[
        "spectral_envelope", "hnr_db_proxy", "formants_hz_estimate", "formant_peak_strength_proxy",
        "aperiodicity_proxy", "breathiness_proxy", "voice_quality_proxy"])
    base["feature_note"] += " P2 HNR/formant/breathiness/aperiodicity outputs are diagnostic proxies, not ground truth."
    arrays = [v for v in base.values() if isinstance(v, np.ndarray)]
    if any(not np.isfinite(a).all() for a in arrays):
        raise FloatingPointError("Feature extraction produced NaN or infinite values")
    n = len(base["frame_times_sec"])
    for key, value in base.items():
        if isinstance(value, np.ndarray) and value.ndim >= 1 and value.shape[0] != n:
            raise RuntimeError(f"Frame count mismatch for {key}: {value.shape[0]} != {n}")
    return base
