from __future__ import annotations
from pathlib import Path
import json

def parse_midi(path: Path):
    try:
        import mido
    except ImportError as e:
        raise RuntimeError("mido is required for MIDI parsing") from e

    mid = mido.MidiFile(str(path))
    tempo = 500000
    ticks_per_beat = mid.ticks_per_beat
    absolute_ticks = 0
    notes = []
    active = {}

    for track_index, track in enumerate(mid.tracks):
        absolute_ticks = 0
        active = {}
        for msg in track:
            absolute_ticks += msg.time
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                active[(track_index, msg.channel, msg.note)] = (
                    absolute_ticks, msg.velocity
                )
            elif msg.type in ("note_off", "note_on") and (
                msg.type == "note_off" or msg.velocity == 0
            ):
                key = (track_index, msg.channel, msg.note)
                if key in active:
                    start_tick, velocity = active.pop(key)
                    start_sec = mido.tick2second(start_tick, ticks_per_beat, tempo)
                    end_sec = mido.tick2second(absolute_ticks, ticks_per_beat, tempo)
                    notes.append({
                        "track": track_index,
                        "channel": msg.channel,
                        "midi": int(msg.note),
                        "velocity": int(velocity),
                        "start": float(start_sec),
                        "end": float(end_sec),
                        "duration": float(max(0.0, end_sec-start_sec))
                    })

    notes.sort(key=lambda x: (x["start"], x["midi"]))
    return {
        "format": 1 if len(mid.tracks) > 1 else 0,
        "ticks_per_beat": ticks_per_beat,
        "notes": notes
    }
