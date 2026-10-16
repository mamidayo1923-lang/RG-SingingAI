from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Phase0Config:
    sample_rate: int = 44100
    channels: int = 1
    fft_size: int = 2048
    hop_size: int = 256
    mel_bins: int = 128
    fmin: float = 20.0
    f0_floor: float = 50.0
    f0_ceil: float = 1200.0
    formant_count: int = 4
    max_formant_hz: float = 5500.0
    clipping_threshold: float = 0.999
    silence_rms_dbfs: float = -60.0
    dc_offset_abs_max: float = 0.01
    max_invalid_f0_ratio: float = 0.70

    @property
    def frame_rate(self) -> float:
        return self.sample_rate / self.hop_size

    @classmethod
    def from_yaml(cls, path: Path) -> "Phase0Config":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        a = data.get("audio", {})
        f = data.get("frame", {})
        m = data.get("mel", {})
        f0 = data.get("f0", {})
        fo = data.get("formants", {})
        qc = data.get("quality_control", {})
        return cls(
            sample_rate=int(a.get("sample_rate", 44100)),
            channels=int(a.get("channels", 1)),
            fft_size=int(f.get("fft_size", 2048)),
            hop_size=int(f.get("hop_size", 256)),
            mel_bins=int(m.get("bins", 128)),
            fmin=float(m.get("fmin", 20.0)),
            f0_floor=float(f0.get("f0_floor", 50.0)),
            f0_ceil=float(f0.get("f0_ceil", 1200.0)),
            formant_count=int(fo.get("count", 4)),
            max_formant_hz=float(fo.get("max_formant_hz", 5500.0)),
            clipping_threshold=float(qc.get("clipping_threshold", 0.999)),
            silence_rms_dbfs=float(qc.get("silence_rms_dbfs", -60.0)),
            dc_offset_abs_max=float(qc.get("dc_offset_abs_max", 0.01)),
            max_invalid_f0_ratio=float(qc.get("max_invalid_f0_ratio", 0.70)),
        )
