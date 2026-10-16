from __future__ import annotations
import warnings
import numpy as np
from scipy.signal import get_window, find_peaks, lfilter

def frame_signal(y, frame_length, hop):
    if len(y) == 0:
        return np.zeros((0, frame_length), dtype=np.float32)
    n = 1 + max(0, int(np.ceil((len(y) - frame_length) / hop)))
    pad = max(0, (n - 1) * hop + frame_length - len(y))
    yp = np.pad(y, (0, pad))
    idx = np.arange(frame_length)[None, :] + hop * np.arange(n)[:, None]
    return yp[idx].astype(np.float32)

def compute_energy(y, fft_size, hop):
    frames = frame_signal(y, fft_size, hop)
    if len(frames) == 0:
        return np.zeros(0, np.float32)
    win = get_window("hann", fft_size, fftbins=True).astype(np.float32)
    rms = np.sqrt(np.mean((frames * win) ** 2, axis=1) + 1e-12)
    return rms.astype(np.float32)

def compute_mel(y, sr, fft_size, hop, bins, fmin, fmax):
    try:
        import librosa
        S = librosa.feature.melspectrogram(
            y=y, sr=sr, n_fft=fft_size, hop_length=hop,
            win_length=fft_size, window="hann",
            n_mels=bins, fmin=fmin, fmax=fmax or sr/2,
            power=2.0
        )
        return librosa.power_to_db(np.maximum(S, 1e-12), ref=1.0).astype(np.float32)
    except ImportError as e:
        raise RuntimeError("librosa is required for Mel extraction") from e

def compute_f0(y, sr, hop, f0_floor, f0_ceil):
    try:
        import pyworld as pw
        x = y.astype(np.float64)
        frame_period = hop / sr * 1000.0
        f0, t = pw.dio(
            x, sr,
            f0_floor=f0_floor,
            f0_ceil=f0_ceil,
            frame_period=frame_period
        )
        f0 = pw.stonemask(x, f0, t, sr)
        return f0.astype(np.float32), t.astype(np.float32), "pyworld"
    except Exception:
        try:
            import librosa
            f0 = librosa.yin(
                y, fmin=f0_floor, fmax=f0_ceil,
                sr=sr, frame_length=2048, hop_length=hop
            )
            return f0.astype(np.float32), (np.arange(len(f0))*hop/sr).astype(np.float32), "librosa-yin"
        except ImportError as e:
            raise RuntimeError("Install pyworld or librosa for F0 extraction") from e

def compute_voicing(f0):
    return (np.isfinite(f0) & (f0 > 0)).astype(np.float32)

def compute_spectral_envelope(y, sr, fft_size, hop):
    # Phase 0 reference implementation:
    # log-magnitude spectral envelope using a stable FFT representation.
    # WORLD spectral envelope is preferred when available and is recorded as such.
    try:
        import pyworld as pw
        x = y.astype(np.float64)
        f0, t = pw.dio(x, sr, frame_period=hop/sr*1000.0)
        f0 = pw.stonemask(x, f0, t, sr)
        sp = pw.cheaptrick(x, f0, t, sr)
        return np.log(np.maximum(sp, 1e-12)).astype(np.float32), "pyworld-cheaptrick"
    except Exception:
        frames = frame_signal(y, fft_size, hop)
        win = get_window("hann", fft_size, fftbins=True).astype(np.float32)
        spec = np.abs(np.fft.rfft(frames * win, axis=1)) + 1e-8
        return np.log(spec).astype(np.float32), "log-rfft-envelope"

def compute_hnr(y, sr, hop, f0):
    frames = frame_signal(y, 2048, hop)
    out = np.zeros(len(frames), dtype=np.float32)
    for i, frame in enumerate(frames):
        if i >= len(f0) or not np.isfinite(f0[i]) or f0[i] <= 0:
            out[i] = 0.0
            continue
        lag = int(round(sr / float(f0[i])))
        if lag <= 0 or lag >= len(frame):
            continue
        a = frame[:-lag]
        b = frame[lag:]
        den = np.sum((a - b) ** 2) + 1e-12
        num = np.sum(a * b) + 1e-12
        ratio = max(num / den, 1e-8)
        out[i] = float(10.0 * np.log10(ratio))
    return out

def compute_formants(y, sr, hop, count=4, max_formant=5500.0):
    # Prefer Praat/Parselmouth. If unavailable, return NaN matrix rather than
    # pretending a fallback has equivalent formant quality.
    out = np.full((int(np.ceil(len(y)/hop)), count), np.nan, dtype=np.float32)
    try:
        import parselmouth
        snd = parselmouth.Sound(y, sampling_frequency=sr)
        duration = snd.duration
        times = np.arange(len(out), dtype=np.float64) * hop / sr
        formant = snd.to_formant_burg(
            time_step=hop/sr,
            max_number_of_formants=count,
            maximum_formant=max_formant
        )
        for i, t in enumerate(times):
            for j in range(count):
                try:
                    v = formant.get_value_at_time(j+1, float(t))
                    out[i, j] = np.float32(v) if np.isfinite(v) else np.nan
                except Exception:
                    pass
        return out, "parselmouth-burg"
    except Exception:
        return out, "unavailable"

def compute_aperiodicity(y, sr, hop):
    try:
        import pyworld as pw
        x = y.astype(np.float64)
        f0, t = pw.dio(x, sr, frame_period=hop/sr*1000.0)
        f0 = pw.stonemask(x, f0, t, sr)
        ap = pw.d4c(x, f0, t, sr)
        return ap.astype(np.float32), "pyworld-d4c"
    except Exception:
        # Keep shape deterministic and explicitly mark this as fallback.
        frames = frame_signal(y, 2048, hop)
        return np.zeros((len(frames), 5), dtype=np.float32), "fallback-zero-unavailable"

def compute_breathiness(hnr, aperiodicity):
    # Derived estimate, not a physical ground truth.
    h = np.asarray(hnr, np.float32)
    if aperiodicity.ndim == 2:
        ap = np.nanmean(aperiodicity, axis=1)
    else:
        ap = aperiodicity
    n = min(len(h), len(ap))
    out = np.zeros(n, dtype=np.float32)
    if n:
        hn = np.clip((20.0 - h[:n]) / 40.0, 0.0, 1.0)
        aa = np.clip(ap[:n], 0.0, 1.0)
        out = np.clip(0.65*hn + 0.35*aa, 0.0, 1.0).astype(np.float32)
    return out

def compute_voice_quality(hnr, breathiness, f0):
    # Continuous derived descriptor:
    # [modal_proxy, breathy_proxy, irregularity_proxy, pitch_proxy]
    n = min(len(hnr), len(breathiness), len(f0))
    out = np.zeros((n, 4), dtype=np.float32)
    if n:
        breath = breathiness[:n]
        modal = 1.0 - breath
        irregular = np.clip((15.0 - hnr[:n]) / 30.0, 0.0, 1.0)
        pitch_proxy = np.clip((np.log2(np.maximum(f0[:n], 1.0)) - 5.0) / 5.0, 0.0, 1.0)
        out[:, 0] = modal
        out[:, 1] = breath
        out[:, 2] = irregular
        out[:, 3] = pitch_proxy
    return out
