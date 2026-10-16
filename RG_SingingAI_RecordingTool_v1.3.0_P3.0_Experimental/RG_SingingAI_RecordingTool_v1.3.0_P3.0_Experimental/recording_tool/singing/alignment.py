"""Auditable MIDI/phoneme alignment helpers.

This module creates an initial alignment from supplied phoneme labels and MIDI note
intervals. It is not a pretrained acoustic forced aligner: phoneme boundaries must be
reviewed or supplied from an aligner such as Montreal Forced Aligner.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def align_labels_to_midi(phonemes: list[dict], notes: list[dict], *, duration_s: float | None = None) -> dict:
    """Map phoneme labels to note intervals using overlap, preserving original MIDI timing.

    phonemes: [{"label": "k"}, ...] or with manually reviewed start/end seconds.
    notes: [{"start": seconds, "end": seconds, "pitch": MIDI integer, "lyric": str?}, ...]
    Missing phoneme timestamps are initialized by distributing labels over note duration;
    this is a draft only and is explicitly flagged as estimated.
    """
    if not phonemes:
        raise ValueError("phonemes must not be empty")
    if not notes:
        raise ValueError("notes must not be empty")
    ns = sorted(notes, key=lambda n: float(n["start"]))
    for n in ns:
        if float(n["end"]) <= float(n["start"]):
            raise ValueError("Each MIDI note must have end > start")
        if not 0 <= int(n["pitch"]) <= 127:
            raise ValueError("MIDI pitch must be in [0,127]")
    end = float(duration_s if duration_s is not None else max(float(n["end"]) for n in ns))
    if end <= 0:
        raise ValueError("duration_s must be positive")
    supplied = all("start" in p and "end" in p for p in phonemes)
    if supplied:
        ps = [{**p, "start": float(p["start"]), "end": float(p["end"])} for p in phonemes]
    else:
        # Weighted by syllabic nucleus vs consonant duration; only a starting hypothesis.
        weights = [1.0 if str(p.get("label", "")).lower() in {"a","i","u","e","o","aa","ii","uu","ee","oo","N"} else 0.45 for p in phonemes]
        total = sum(weights)
        cursor = 0.0
        ps = []
        for p, w in zip(phonemes, weights):
            nxt = cursor + end * w / total
            ps.append({**p, "start": cursor, "end": nxt})
            cursor = nxt
    aligned = []
    for p in ps:
        mid = (p["start"] + p["end"]) / 2
        candidates = [n for n in ns if float(n["start"]) <= mid < float(n["end"])]
        note = candidates[0] if candidates else min(ns, key=lambda n: min(abs(mid-float(n["start"])), abs(mid-float(n["end"]))))
        aligned.append({"phoneme": str(p.get("label", "?")), "start": p["start"], "end": p["end"],
                        "midi_pitch": int(note["pitch"]), "midi_note_start": float(note["start"]),
                        "midi_note_end": float(note["end"]), "boundary_source": "provided" if supplied else "estimated_duration_distribution"})
    return {"schema_version":"0.1", "method":"label-to-MIDI overlap mapping; not acoustic forced alignment",
            "needs_manual_review": not supplied, "phonemes": aligned}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phonemes", required=True, help="JSON array of {label} or {label,start,end}")
    ap.add_argument("--notes", required=True, help="JSON array of {start,end,pitch}")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    result = align_labels_to_midi(load_json(a.phonemes), load_json(a.notes), duration_s=a.duration)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out)
    print(f"Wrote {out}; needs_manual_review={result['needs_manual_review']}")
if __name__ == "__main__": main()
