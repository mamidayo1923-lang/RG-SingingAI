# RG Singing AI Recording Tool v1.3.0-P2.1

A local recording tool for Windows 10/11 and Python 3.10+. It does not implement external APIs or telemetry. Based on v1.1.0, P0 (data specifications, QC, MIDI reference annotations, and pre-launch validation) has been reflected.

## Launch (PowerShell)
Run in the extraction folder. The first run creates a virtual environment and installs dependent libraries.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

## Features
- 44.1 kHz, mono, PCM 24-bit WAV recording
- Input device selection, recording start/stop, elapsed time display
- Click sound and A4=440 Hz reference tone (not mixed into the recording file)
- Loads MIDI notes, tempo, and time signature, displaying a simple treble clef staff and lyrics
- TXT/LRC lyrics loading, automatic Take ID numbering
- Saves MIDI/lyrics reference files, metadata JSON, and QC JSON
- Saves reference annotation JSON for MIDI note events (clearly distinguished from audio alignment)
- WAV SHA-256 calculation, metadata schema validation, atomic saving of JSON via temporary files
- Inspects Python/Tkinter/main dependent modules before launching
- QC: Sample rate, channels, format, duration, peak/RMS dBFS, silence ratio, clipping ratio

## Data Structure
Saves WAV files in `RG_SingingAI_Dataset/raw/audio/`, metadata in `metadata/`, reference files in `reference/midi/` and `reference/lyrics/`, MIDI note references in `annotations/note/`, and quality reports in `qc/`. For metadata specifications, see `dataset_template/metadata.schema.json`.

## QC Evaluation
- `FAIL`: Errors such as empty file, or sample rate/channels/format differing from specifications
- `WARN`: Possibility of peak near full scale, high silence ratio, low RMS, etc. Recordings are not automatically discarded due to rests or breaths
- `PASS`: No above errors or warnings

## Important Alignment Constraints
`annotations/note/*.json` is reference data recording MIDI note events in seconds and ticks. It does not automatically estimate phoneme boundaries on the recorded waveform. Do not equate MIDI note start times with audio onset times; audio/phoneme alignment must be verified and manually corrected in a separate process. TXT lyrics are character-based, LRC is time-based approximate allocation, and correspondence between Japanese mora/phoneme and musical notes requires manual verification.

## Known Limitations
The score is a simplified display and not engraving equivalent to published sheet music. Accurate stems/beams based on note values, complete notation of rests, ties, dots, tuplets, key signatures, contextual enharmonic judgment, and strict measure reconstruction upon time signature changes are unimplemented. Verify actual operation of recording equipment with the target PC's microphone/drivers. Headphones are recommended.


## P1 additions

### Baseline acoustic feature extraction

```powershell
.\.venv\Scripts\python.exe .\tools\extract_baseline_features.py .\RG_SingingAI_Dataset\raw\audio\S001_010001.wav
```

Writes a compressed NPZ containing `log_mel`, `f0_hz`, `frame_times_sec`, and the serialized feature config. The autocorrelation F0 estimator is deliberately a **diagnostic baseline**, not a production pitch tracker. It does not perform phoneme alignment and does not generate singing audio.

### Group-aware data split

Before running, add a `group_id`, `phrase_id`, `song_id`, or `source_group_id` to each metadata JSON. The grouping key should identify the highest-level shared musical material that must not cross dataset partitions (prefer song/phrase grouping over individual takes).

```powershell
.\.venv\Scripts\python.exe .\tools\make_splits.py --metadata-dir .\RG_SingingAI_Dataset\metadata --output .\RG_SingingAI_Dataset\splits\split_manifest.json --seed 20261015 --group-key song_id
```

The tool fails when grouping metadata is missing rather than silently splitting takes independently. Because groups can have different sizes, the final item proportions may differ from 80/10/10; group integrity takes precedence.

### Evaluation helpers

`recording_tool.evaluation` provides F0 RMSE/MAE and gross error rate on voiced reference/prediction pairs, plus onset MAE in milliseconds. These metrics require a trusted reference; they do not automatically establish correctness of estimated F0 or note boundaries. Listening tests remain necessary.

## Data metadata update

To prevent split leakage, future recordings should include at least one of `group_id`, `phrase_id`, `song_id`, or `source_group_id`. The recording GUI provides optional fields for song_id, phrase_id, and group_id. Use each grouping key consistently across related takes before generating splits.


## P2 additions
- Preserves P1 recording, score, MIDI reference, QC, deterministic group split and baseline features.
- GUI now optionally captures `song_id`, `phrase_id`, and `group_id` in take metadata for leakage-resistant dataset splitting. Use the same grouping key consistently across takes.
- `tools/extract_baseline_features.py` now emits P1 log-Mel/F0 plus P2 spectral envelope, HNR proxy, coarse formant estimates, aperiodicity, breathiness and voice-quality proxy arrays to NPZ.
- P2 descriptors are diagnostic approximations, not calibrated ground truth. No MIDI/audio forced alignment is claimed.

### Extract P2 features
`python tools/extract_baseline_features.py path\to\take.wav --output path\to\take.features_p2.npz`


## P2.1 hardening and validation
- P1/P2 recording and dataset functions are retained.
- Feature extraction uses FFT-based autocorrelation, includes a parabolic lag interpolation and an explicitly uncalibrated F0-confidence proxy.
- The spectral-envelope estimate uses cepstral smoothing; formant peak-strength proxy is saved separately.
- Input validation rejects missing, empty, non-mono, wrong-rate, and non-finite audio. Numeric outputs are checked for finite values and consistent frame counts.
- NPZ files are written through a temporary file and atomic replacement. Existing outputs are protected unless `--overwrite` is specified.
- Frame timestamps remain frame-start timestamps; no center correction or audio/phoneme/MIDI alignment is inferred.
- All HNR/formant/breathiness/aperiodicity/voice-quality fields remain diagnostic proxies and must not be treated as ground truth.

### Extraction command
```powershell
.\.venv\Scripts\python.exe .\tools\extract_baseline_features.py `
  ".\RG_SingingAI_Dataset\raw\audio\S001_010001.wav"
```
To intentionally replace an existing output, add `--overwrite`.

### Automated tests
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```


## P3.0 experimental research modules

This release adds experimental alignment utilities, optional WORLD-based acoustic analysis, a trainable phoneme/pitch-conditioned log-mel network, and a Griffin-Lim rendering baseline. These are research scaffolds, **not** a completed high-fidelity singing synthesizer.

### Optional install (Windows / PowerShell)

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ml]"
# Optional acoustic-analysis extra (pyworld wheel availability depends on Python/platform):
.\.venv\Scripts\python.exe -m pip install -e ".[acoustic]"
```

### Alignment draft

Prepare `phonemes.json` and `notes.json` as valid JSON. Example `phonemes.json`:

```json
[{"label":"k"},{"label":"a"}]
```

Example `notes.json`:

```json
[{"start":0.0,"end":0.5,"pitch":60}]
```

Then run:

```powershell
.\.venv\Scripts\python.exe .\tools\align_phonemes_midi.py --phonemes .\phonemes.json --notes .\notes.json --duration 0.5 --out .\alignment.json
```

When no phoneme timestamps are supplied, boundaries are only duration-distribution guesses and `needs_manual_review` is true. This is not audio-conditioned forced alignment.

### Acoustic analysis

```powershell
.\.venv\Scripts\python.exe -c "from recording_tool.singing.acoustic import analyze_world; import numpy as np; r=analyze_world('voice.wav'); np.savez_compressed('world_features.npz', **{k:v for k,v in r.items() if isinstance(v,np.ndarray)}); print(r['metadata'])"
```

WORLD F0 and spectral features are algorithmic estimates, not calibrated measurements. HNR and formant candidates require validation against reference labels; microphone/room calibration is not implemented.

### Neural training data contract

Each training NPZ must contain frame-aligned arrays `log_mel[T,80]`, `phoneme_ids[T]`, `midi_pitch[T]`, and `velocity[T]`. Existing P2 feature NPZs do not automatically contain phoneme/MIDI frame labels. Create/verify alignments first; do not treat missing labels as zeros.

```powershell
.\.venv\Scripts\python.exe -m recording_tool.singing.train --data .\training_frames --vocab-size 128 --epochs 50 --out .\models\singing_melnet.pt
.\.venv\Scripts\python.exe .\tools\render_singing.py --model .\models\singing_melnet.pt --score .\score_frames.json --out .\generated.wav
```

The current renderer uses mel inversion + Griffin-Lim, which typically sounds buzzy/noisy and does not provide a production neural vocoder. The model does not yet learn duration, phoneme transitions, vibrato, expressive timing, or singer identity robustly.


## P3.1 Dataset Pipeline

See `docs/P3.1_DATASET_PIPELINE.md` for annotation format, dataset generation, training commands, and limitations. Dataset generation requires reviewed phoneme timestamps; this tool is not an acoustic forced aligner.


## Feature / F0 QC GUI (added)
Launch with PowerShell:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_feature_qc_gui.ps1
```
The GUI can select a mono 44.1 kHz WAV and extract P1/P2 diagnostic features to NPZ, load an existing NPZ, plot F0/confidence-proxy/RMS, flag low-confidence/low-RMS/large-adjacent-F0-jump frames, inspect flagged rows, and export the QC table to CSV. Thresholds are editable. Original NPZ values are not changed and no automatic pitch correction is applied. A flag is a review candidate, not proof of an error. HNR/formant/breathiness/aperiodicity outputs remain diagnostic proxies.


## P3.3 QC visibility improvements

- Red `×` markers on the F0 plot indicate large adjacent F0 jumps.
- Orange outlined circles on the confidence plot indicate low-confidence frames.
- Red circles on the RMS plot indicate low-RMS frames.
- Select a QC table row to show a red dashed cursor and zoom to the surrounding 1.5-second interval. Use **Show All** to restore the full timeline.
- The on-screen table prioritizes actionable flags (low confidence, low RMS, large F0 jump). CSV output continues to include all frames and flags.


## P3.4 QC table markers

The QC frame list now shows visible symbols in its finding column: `× Large F0 jump`, `○ Low confidence`, `● Low RMS`, and `— Unestimated F0/unvoiced candidate`. Row text color helps distinguish the finding type; combined findings use a separate color. The exported CSV keeps the original machine-readable flag values.
