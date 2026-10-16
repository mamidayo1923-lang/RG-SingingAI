from __future__ import annotations
from pathlib import Path
import json
import platform
import sys
from datetime import datetime, timezone

from .config import Phase0Config
from .audio import read_audio, audio_qc
from .features import (
    compute_energy, compute_mel, compute_f0, compute_voicing,
    compute_spectral_envelope, compute_hnr, compute_formants,
    compute_aperiodicity, compute_breathiness, compute_voice_quality
)
from .io_utils import ensure_dirs, save_json, save_npy
from .midi import parse_midi
from .alignment import build_score_alignment
from .phoneme import load_phoneme_json, validate_phonemes
from .qc import feature_qc

def _now():
    return datetime.now(timezone.utc).isoformat()

def build_sample(dataset: Path, audio_path: Path, cfg: Phase0Config):
    ensure_dirs(dataset)
    audio_path = Path(audio_path)
    sample_id = audio_path.stem

    y, sr, info = read_audio(audio_path, cfg.sample_rate)
    aqc = audio_qc(y, cfg)

    features = {}
    f0, f0_time, f0_method = compute_f0(
        y, sr, cfg.hop_size, cfg.f0_floor, cfg.f0_ceil
    )
    energy = compute_energy(y, cfg.fft_size, cfg.hop_size)
    mel = compute_mel(y, sr, cfg.fft_size, cfg.hop_size, cfg.mel_bins, cfg.fmin, None)
    voicing = compute_voicing(f0)
    spectral, spectral_method = compute_spectral_envelope(y, sr, cfg.fft_size, cfg.hop_size)
    hnr = compute_hnr(y, sr, cfg.hop_size, f0)
    formants, formant_method = compute_formants(
        y, sr, cfg.hop_size, cfg.formant_count, cfg.max_formant_hz
    )
    aperiodicity, ap_method = compute_aperiodicity(y, sr, cfg.hop_size)
    breathiness = compute_breathiness(hnr, aperiodicity)
    voice_quality = compute_voice_quality(hnr, breathiness, f0)

    features.update({
        "f0": f0,
        "energy": energy,
        "voicing": voicing,
        "mel": mel,
        "spectral_envelope": spectral,
        "hnr": hnr,
        "formants": formants,
        "aperiodicity": aperiodicity,
        "breathiness": breathiness,
        "voice_quality": voice_quality
    })

    for name, arr in features.items():
        save_npy(dataset / "features" / name / f"{sample_id}.npy", arr)

    midi_path = dataset / "reference" / "midi" / f"{sample_id}.mid"
    midi_data = None
    alignment = None
    if midi_path.exists():
        midi_data = parse_midi(midi_path)
        save_json(dataset / "annotations" / "note" / f"{sample_id}.json", midi_data)
        alignment = build_score_alignment(midi_data["notes"])
        save_json(dataset / "annotations" / "alignment" / f"{sample_id}.json",
                  {"sample_id": sample_id, "notes": alignment})

    phoneme_path = dataset / "annotations" / "phoneme" / f"{sample_id}.json"
    phoneme_errors = []
    if phoneme_path.exists():
        ph = load_phoneme_json(phoneme_path)
        phoneme_errors = validate_phonemes(ph)

    feature_report = feature_qc(features, cfg)
    report = {
        "schema_version": "1.0.0",
        "dataset_version": "1.0.0",
        "sample_id": sample_id,
        "created_utc": _now(),
        "python": sys.version,
        "platform": platform.platform(),
        "audio": {
            "source": str(audio_path),
            "sample_rate": sr,
            "channels": int(info.channels),
            "subtype": info.subtype,
            "frames": int(info.frames),
            "duration_sec": float(len(y)/sr)
        },
        "audio_qc": aqc,
        "frame": {
            "fft_size": cfg.fft_size,
            "hop_size": cfg.hop_size,
            "frame_rate_hz": cfg.frame_rate
        },
        "extractors": {
            "f0": f0_method,
            "spectral_envelope": spectral_method,
            "formants": formant_method,
            "aperiodicity": ap_method,
            "breathiness": "derived_hnr_aperiodicity_estimate",
            "voice_quality": "derived_continuous_descriptor"
        },
        "features": {
            name: {
                "shape": list(arr.shape),
                "dtype": str(arr.dtype)
            } for name, arr in features.items()
        },
        "phoneme_validation_errors": phoneme_errors,
        "feature_qc": feature_report,
        "status": "warning" if phoneme_errors or aqc["clipping_detected"] else "ok"
    }
    save_json(dataset / "qc" / f"{sample_id}.json", report)

    manifest = {
        "sample_id": sample_id,
        "audio": f"raw/audio/{sample_id}.wav",
        "features": {
            name: f"features/{name}/{sample_id}.npy"
            for name in features
        },
        "annotations": {
            "phoneme": f"annotations/phoneme/{sample_id}.json",
            "note": f"annotations/note/{sample_id}.json" if midi_data else None,
            "alignment": f"annotations/alignment/{sample_id}.json" if alignment else None
        },
        "qc": f"qc/{sample_id}.json"
    }
    save_json(dataset / "manifests" / f"{sample_id}.json", manifest)
    return report

def build_dataset(dataset: Path, cfg: Phase0Config):
    ensure_dirs(dataset)
    audio_dir = dataset / "raw" / "audio"
    reports = []
    for audio in sorted(audio_dir.glob("*.wav")):
        try:
            reports.append(build_sample(dataset, audio, cfg))
        except Exception as e:
            reports.append({
                "sample_id": audio.stem,
                "status": "error",
                "error": str(e)
            })
    save_json(dataset / "manifests" / "dataset_manifest.json", {
        "schema_version": "1.0.0",
        "dataset_version": "1.0.0",
        "generated_utc": _now(),
        "sample_count": len(reports),
        "samples": reports
    })
    return reports
