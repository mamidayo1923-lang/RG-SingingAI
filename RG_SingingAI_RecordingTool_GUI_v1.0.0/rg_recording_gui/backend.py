"""Backend adapter. Keeps GUI independent from future RecordingTool changes."""
from __future__ import annotations
import json, os, wave, math, struct, threading, time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class RecordingSettings:
    output_dir: Path
    sample_rate: int = 44100
    channels: int = 1
    sample_width: int = 3
    device: int | None = None

class RecordingBackend:
    """Minimal local WAV recording adapter; imports sounddevice only when recording starts."""
    def __init__(self):
        self._stream = None
        self._frames = []
        self._lock = threading.Lock()
        self._recording = False
        self._settings = None
        self._started = None

    def devices(self):
        try:
            import sounddevice as sd
            return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
        except Exception:
            return []

    def start(self, settings: RecordingSettings):
        import sounddevice as sd
        if self._recording:
            raise RuntimeError("すでに録音中です。")
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        self._frames = []
        self._settings = settings
        self._started = time.time()
        def callback(indata, frames, time_info, status):
            with self._lock:
                self._frames.append(bytes(indata))
        self._stream = sd.RawInputStream(samplerate=settings.sample_rate,
            channels=settings.channels, dtype="int24", device=settings.device,
            callback=callback)
        self._stream.start()
        self._recording = True

    def stop(self, speaker_id="SPK001", session_id="SESSION001", take_number=1):
        if not self._recording:
            raise RuntimeError("録音中ではありません。")
        self._stream.stop()
        self._stream.close()
        self._recording = False
        with self._lock:
            data = b"".join(self._frames)
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = f"{speaker_id}_{session_id}_TAKE{take_number:04d}_{now}"
        wav_path = self._settings.output_dir / f"{stem}.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(self._settings.channels)
            wf.setsampwidth(self._settings.sample_width)
            wf.setframerate(self._settings.sample_rate)
            wf.writeframes(data)
        duration = len(data) / (self._settings.sample_rate * self._settings.channels * self._settings.sample_width)
        metadata = {
            "schema_version": "1.0", "created_at": datetime.now().isoformat(timespec="seconds"),
            "speaker_id": speaker_id, "session_id": session_id, "take_number": take_number,
            "audio": {"file": wav_path.name, "sample_rate": self._settings.sample_rate,
                      "channels": self._settings.channels, "sample_format": "PCM_24",
                      "duration_seconds": round(duration, 4), "frames_bytes": len(data)},
            "qc": {"duration_seconds": round(duration, 4), "empty_audio": len(data) == 0,
                   "status": "REVIEW_REQUIRED"}
        }
        (self._settings.output_dir / f"{stem}.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return wav_path, duration

    @property
    def recording(self): return self._recording
