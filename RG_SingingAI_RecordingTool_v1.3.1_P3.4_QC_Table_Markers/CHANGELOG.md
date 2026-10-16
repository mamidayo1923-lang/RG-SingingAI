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


## v1.3.0-P2 (2026-10-15)
- Added diagnostic spectral-envelope, HNR proxy, coarse formant, aperiodicity, breathiness and voice-quality features.
- Added optional song/phrase/group IDs to recording metadata from GUI.
- Extended NPZ feature export; P1 behavior and interfaces remain available.
- Explicitly documented estimator limitations; no forced alignment or production-grade F0/HNR claims.


## v1.3.0-P2.1 (2026-10-15)
- Preserved all P0/P1/P2 recording, MIDI, score, QC, metadata, dataset-split, and feature-extraction functions.
- Replaced repeated direct autocorrelation with FFT-based linear autocorrelation for lower computational cost.
- Added parabolic lag interpolation and an explicitly uncalibrated F0 confidence proxy.
- Replaced the short-bin moving-average envelope with cepstral smoothing; added a formant peak-strength proxy.
- Added strict input checks, finite-output checks, and cross-feature frame-count consistency checks.
- NPZ extraction now writes atomically and refuses to overwrite existing outputs unless `--overwrite` is passed.
- Fixed GUI log line breaks and expanded automated tests.
- Important: P2 values remain diagnostic proxies. This release does not add forced alignment or a singing synthesis model.

## 1.3.1-P3.1 (2026-10-15)
- Added reviewed-annotation WAV-to-frame-aligned-NPZ dataset builder and schema checks.
- Added stronger training-array validation and train/validation MSE logging with best-checkpoint saving.
- Hardened phoneme/MIDI interval validation and added dataset-builder tests.
- Preserved the P0/P1/P2 recording, QC, feature extraction, and split tools.
- Limitations remain: no acoustic forced aligner, shared vocabulary consolidation, production vocoder, or validated perceptual singing quality.


## 1.3.1-P3.3 — 2026-10-15 (QC location visibility)
- Added direct graph markers for large F0 jumps, low-confidence frames, and low-RMS frames.
- Selecting a QC finding now draws a red vertical cursor and zooms to a 1.5-second neighborhood.
- Added a one-click full-timeline view and selected-frame detail line.
- Reduced table noise by excluding unvoiced/unestimated-only rows from the on-screen findings list; these remain included in CSV results.
- Preserved source NPZ data; QC remains diagnostic and does not auto-correct F0.


## 1.3.1-P3.4 — 2026-10-15 (QC table markers)
- Added explicit symbols in the QC frame list: × large F0 jump, ○ low confidence, ● low RMS, — unvoiced/unestimated candidate.
- Added row text colors to distinguish single-type and multi-type QC findings.
- Kept underlying CSV flag values and original NPZ data unchanged.
