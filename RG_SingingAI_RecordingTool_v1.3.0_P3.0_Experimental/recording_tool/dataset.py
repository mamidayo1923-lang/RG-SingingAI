"""Versioned dataset metadata and integrity helpers for Phase 0."""
from pathlib import Path
import hashlib, json, os, tempfile

METADATA_SCHEMA_VERSION = "1.0.0"

def sha256_file(path, block_size=1024*1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            h.update(block)
    return h.hexdigest()

def atomic_write_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(temp_name, path)
    except Exception:
        try: os.unlink(temp_name)
        except OSError: pass
        raise

def validate_metadata(meta):
    errors=[]
    required=("metadata_schema_version","created_at","speaker_id","session_id","take_id","audio")
    for key in required:
        if key not in meta: errors.append(f"必須キーがありません: {key}")
    audio=meta.get("audio", {})
    for key in ("path","sample_rate","channels","subtype","duration_sec","sha256"):
        if key not in audio: errors.append(f"audio.{key} がありません")
    if audio.get("sample_rate") != 44100: errors.append("audio.sample_rate は 44100 である必要があります")
    if audio.get("channels") != 1: errors.append("audio.channels は 1 である必要があります")
    if audio.get("subtype") != "PCM_24": errors.append("audio.subtype は PCM_24 である必要があります")
    if not isinstance(audio.get("duration_sec"), (int,float)) or audio.get("duration_sec",0) <= 0: errors.append("audio.duration_sec は正の数である必要があります")
    if meta.get("alignment", {}).get("status") not in ("not_available", "midi_event_reference_pending_audio_alignment", "manually_verified"):
        errors.append("alignment.status が不正です")
    return {"schema_version":METADATA_SCHEMA_VERSION,"passed":not errors,"errors":errors}

def build_note_reference(midi, lyrics):
    """MIDI note reference only; deliberately does not claim audio/phoneme alignment."""
    events=[]
    for i,n in enumerate(midi.notes):
        events.append({"event_id":f"N{i+1:05d}","pitch_midi":int(n.pitch),"pitch_name":_pitch_name(n.pitch),
          "velocity":int(n.velocity),"start_tick":int(n.start),"end_tick":int(n.end),
          "start_sec":round(float(n.start_sec),6),"end_sec":round(float(n.end_sec),6),
          "duration_sec":round(float(n.end_sec-n.start_sec),6),"lyric_text":lyrics[i] if i<len(lyrics) else "",
          "audio_alignment_status":"not_aligned"})
    return {"annotation_schema_version":"1.0.0","source":"MIDI note events; audio boundaries are not inferred",
      "alignment_status":"midi_event_reference_pending_audio_alignment","ticks_per_beat":int(midi.tpb),
      "tempo_events":[{"tick":int(t),"microseconds_per_beat":int(v)} for t,v in midi.tempos],
      "time_signatures":[{"tick":int(t),"numerator":int(n),"denominator":int(d)} for t,n,d in midi.signatures],
      "notes":events,"limitations":["MIDIノート時刻は録音音声の音素境界を意味しません","歌詞の自動割当ては参考情報であり手動確認が必要です"]}

def _pitch_name(n):
    names=("C","C#","D","D#","E","F","F#","G","G#","A","A#","B")
    return f"{names[int(n)%12]}{int(n)//12-1}"
