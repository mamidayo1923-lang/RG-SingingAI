RG Singing AI dataset layout (v1.2.0)

raw/audio/                  PCM_24 mono WAV, 44100 Hz
metadata/                   one JSON per take; schema metadata.schema.json
reference/midi/             original MIDI source copy
reference/lyrics/           original TXT/LRC source copy
annotations/note/            MIDI note-event reference JSON (NOT audio alignment)
annotations/alignment/      reserved for verified audio/phoneme boundaries
qc/                         machine-readable QC report per take

Important: MIDI note times are not automatically treated as audio or phoneme boundaries. QC silence is a warning because rests and breaths are valid. Audio SHA-256 is stored in metadata.

P1: FEATURE_SPEC.json documents baseline feature configuration. For train/validation/test splitting, add group_id/phrase_id/song_id/source_group_id to metadata and use tools/make_splits.py. Keep related takes from the same phrase/song in one split.
