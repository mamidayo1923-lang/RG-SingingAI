# Changelog

## 1.3.0 — 2026-10-15 (P1 implementation)
- Added versioned baseline feature configuration and dependency-light log-mel/F0 diagnostic extraction.
- Added group-aware train/validation/test split generation; groups are kept intact to reduce phrase/song leakage.
- Added F0 RMSE/MAE/gross-error and onset MAE evaluation helpers.
- Added CLI tools and P1 unit tests.
- Preserved v1.2.0 recording, QC, metadata, MIDI reference annotation and GUI functions.
- Explicitly labels baseline F0 as diagnostic, not production-grade; no forced alignment or trained synthesis model is claimed.


## 1.2.0 — 2026-10-15 (P0 implementation)
- Added a versioned metadata contract and JSON schema template.
- Added SHA-256 integrity hash for recorded WAV files.
- Made JSON writes atomic to reduce partial metadata/QC files after interruption.
- Changed QC to distinguish hard errors from warnings; silence and near-full-scale peaks are warnings rather than automatic rejection.
- Added explicit metadata validation before metadata is committed.
- Added MIDI note-event reference annotations with ticks, seconds, tempo, time signatures, lyric text, and explicit `not_aligned` status.
- Added startup preflight checks for Python/Tkinter and core dependencies.
- Added unit tests for QC, JSON writes, hash generation, and metadata validation.
- Preserved existing recording, device selection, click/reference tones, MIDI/lyrics display, take numbering, and source-file copies.

## Limitations
- MIDI note-event annotations do not constitute waveform/phoneme forced alignment.
- The full GUI and physical audio-device behavior must still be tested on Windows 10/11.
