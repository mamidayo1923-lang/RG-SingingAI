# RG Singing AI — Phase 0 Dataset Builder v1.0.0

歌声合成AI向けの学習Datasetを構築するためのローカル専用ツールです。

## Phase 0 の目的

Original WAVを変更せず保存し、以下の情報を再現可能な形で抽出します。

- F0
- Energy
- Voicing
- Mel Spectrogram
- Spectral Envelope
- HNR
- Formants
- Aperiodicity
- Breathiness (estimated)
- Voice Quality (estimated)
- Phoneme annotation
- MIDI note annotation
- Score / performed alignment
- Dataset manifest
- QC report

## 標準音声仕様

- WAV / PCM
- 44.1 kHz
- 24-bit推奨
- Mono
- Original audio is never normalized or overwritten

## 標準フレーム仕様

- sample_rate = 44100
- fft_size = 2048
- hop_size = 256
- Hann window
- frame_rate = 44100 / 256 = 172.265625 Hz
- mel_bins = 128
- fmin = 20 Hz
- fmax = Nyquist

## 必須 / オプション依存

最小構成:
- Python 3.11+
- numpy
- scipy
- soundfile
- PyYAML

高品質特徴:
- librosa
- pyworld
- parselmouth

MIDI:
- mido

Alignment / phonemizerは将来差し替え可能なAdapterとして設計しています。

## セットアップ

PowerShell:

```powershell
cd RG_SingingAI_Phase0_v1.0.0
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

推奨追加:

```powershell
pip install pyworld librosa mido praat-parselmouth
```

## ディレクトリ

```text
RG_SingingAI_Dataset/
├─ raw/
│  ├─ audio/
│  └─ recording_metadata/
├─ reference/
│  ├─ midi/
│  └─ lyrics/
├─ annotations/
│  ├─ phoneme/
│  ├─ note/
│  └─ alignment/
├─ features/
│  ├─ f0/
│  ├─ energy/
│  ├─ voicing/
│  ├─ mel/
│  ├─ spectral_envelope/
│  ├─ hnr/
│  ├─ formants/
│  ├─ aperiodicity/
│  ├─ breathiness/
│  └─ voice_quality/
├─ manifests/
├─ qc/
└─ logs/
```

Dataset作成:

```powershell
python -m rg_singing_ai_phase0 build --dataset .\RG_SingingAI_Dataset
```

単一音声:

```powershell
python -m rg_singing_ai_phase0 extract --dataset .\RG_SingingAI_Dataset --audio S001_000001.wav
```

Dataset検査:

```powershell
python -m rg_singing_ai_phase0 qc --dataset .\RG_SingingAI_Dataset
```

## 重要

Phase 0では、Breathiness / Voice Qualityは物理的な唯一の正解値として扱いません。
複数の音響特徴から推定したderived featureとして保存します。

また、MIDIからの「score timing」と実際の録音上の「performed timing」は別概念です。
Phase 0ではその2つを別々に保持し、alignment情報を後から更新できるようにします。
