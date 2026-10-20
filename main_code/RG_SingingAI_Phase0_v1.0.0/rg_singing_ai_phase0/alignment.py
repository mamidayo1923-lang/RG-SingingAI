from __future__ import annotations

def build_score_alignment(notes):
    # Phase 0 stores score timing as a separate timeline.
    # Performed timing is intentionally left editable because automatic
    # forced-alignment quality depends on the selected aligner and recording.
    return [
        {
            "note_index": i,
            "midi": n["midi"],
            "score_start": n["start"],
            "score_end": n["end"],
            "performed_start": None,
            "performed_end": None,
            "alignment_status": "unresolved"
        }
        for i, n in enumerate(notes)
    ]
