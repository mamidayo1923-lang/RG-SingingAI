# Phase 0 Dataset Specification v1.0.0

## Audio
- WAV PCM
- 44.1 kHz
- mono
- 24-bit recommended
- original preserved
- no silent normalization/resampling

## Frame
- FFT 2048
- hop 256
- Hann
- 172.265625 frames/sec

## Features
1. F0
2. Energy
3. Voicing
4. Mel spectrogram
5. Spectral envelope
6. HNR
7. Formants F1-F4
8. Aperiodicity
9. Breathiness estimate
10. Voice quality continuous descriptor

## Annotations
- phoneme intervals
- MIDI notes
- score timing
- performed timing
- alignment status

## Storage
- numeric features: NumPy .npy, float32
- metadata/QC: JSON UTF-8
- source MIDI: original .mid
- source WAV: original .wav

## Important distinction

Breathiness and voice quality are not treated as immutable physical ground-truth values.
They are derived/estimated features and their extraction method/version is recorded.

## Alignment

Score timing and performed timing are independent.
Automatic forced alignment is intentionally not hard-coded into the Dataset schema.
This permits replacement of the aligner without changing the raw data.
