"""Recording quality checks. Silence is a warning, not automatically a failure."""
from pathlib import Path
import numpy as np
import soundfile as sf

TARGET_SAMPLE_RATE = 44100
TARGET_CHANNELS = 1
TARGET_SUBTYPE = "PCM_24"

def inspect(path):
    path = Path(path)
    info = sf.info(str(path))
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if x.size else 0.0
    db = lambda v: round(20 * np.log10(max(float(v), 1e-12)), 2)
    # Frame-level silence indicator; intentional rests/breaths can also trigger this.
    frame_peak = np.max(np.abs(x), axis=1) if len(x) else np.array([], dtype=np.float32)
    silence_ratio = float(np.mean(frame_peak < 0.001)) if len(frame_peak) else 1.0
    clipping_ratio = float(np.mean(frame_peak >= 0.999)) if len(frame_peak) else 0.0
    errors, warnings = [], []
    if info.frames <= 0: errors.append("音声データが空です")
    if sr != TARGET_SAMPLE_RATE: errors.append(f"サンプルレートが仕様と異なります: {sr} Hz (期待値 {TARGET_SAMPLE_RATE} Hz)")
    if info.channels != TARGET_CHANNELS: errors.append(f"チャンネル数が仕様と異なります: {info.channels} (期待値 {TARGET_CHANNELS})")
    if info.subtype != TARGET_SUBTYPE: errors.append(f"音声形式が仕様と異なります: {info.subtype} (期待値 {TARGET_SUBTYPE})")
    if peak >= 0.999: warnings.append("ピークがフルスケール付近です。クリッピングの有無を確認してください")
    if clipping_ratio > 0: warnings.append("フルスケール付近のサンプルを検出しました")
    if silence_ratio > 0.25: warnings.append("無音率が高めです。休符・ブレス・録音開始前後の無音を考慮して確認してください")
    if rms < 0.003 and info.frames > 0: warnings.append("RMSレベルが非常に低い可能性があります")
    return {
      "qc_schema_version":"1.0.0", "sample_rate":sr, "channels":info.channels,
      "subtype":info.subtype, "frames":int(info.frames), "duration_sec":round(float(info.duration), 6),
      "peak_dbfs":db(peak), "rms_dbfs":db(rms), "silence_ratio":round(silence_ratio, 6),
      "clipping_ratio":round(clipping_ratio, 8), "errors":errors, "warnings":warnings,
      "passed":not errors, "status":"FAIL" if errors else ("WARN" if warnings else "PASS"),
      "interpretation":"無音率・ピークは自動判定だけで録音を破棄せず、休符やブレスを含めて確認してください"
    }
