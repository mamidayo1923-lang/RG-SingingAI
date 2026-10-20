# RG Singing AI Recording Tool v1.3.0-P2.1

Windows 10/11、Python 3.10+向けのローカル録音ツールです。外部APIやテレメトリは実装していません。v1.1.0を基に、P0（データ仕様・QC・MIDI参照注釈・起動前検証）を反映しました。

## 起動（PowerShell）
展開先で実行します。初回は仮想環境と依存ライブラリを作成します。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

## 機能
- 44.1 kHz、モノラル、PCM 24-bit WAV録音
- 入力デバイス選択、録音開始/停止、経過時間表示
- クリック音とA4=440 Hz基準音（録音ファイルにはミックスしません）
- MIDIノート、テンポ、拍子を読み込み、ト音記号の簡易五線譜と歌詞を表示
- TXT/LRC歌詞読み込み、Take ID自動採番
- MIDI/歌詞参照ファイル、メタデータJSON、QC JSONを保存
- MIDIノートイベントの参照注釈JSONを保存（音声アラインメントとは明確に区別）
- WAVのSHA-256、メタデータスキーマ検証、JSONの一時ファイル経由での原子的保存
- 起動前にPython/Tkinter/主要依存モジュールを検査
- QC: サンプルレート、チャンネル、形式、長さ、ピーク/RMS dBFS、無音率、クリッピング率

## データ構造
`RG_SingingAI_Dataset/raw/audio/` にWAV、`metadata/` にメタデータ、`reference/midi/` と `reference/lyrics/` に参照ファイル、`annotations/note/` にMIDIノート参照、`qc/` に品質レポートを保存します。メタデータ仕様は `dataset_template/metadata.schema.json` を参照してください。

## QC判定
- `FAIL`: ファイルが空、またはサンプルレート/チャンネル/形式が仕様と異なるなどのエラー
- `WARN`: ピークがフルスケール付近、無音率が高い、RMSが低い可能性など。休符やブレスがあるため自動的に録音を破棄しません
- `PASS`: 上記エラー・警告なし

## アラインメント上の重要な制約
`annotations/note/*.json` は MIDI のノートイベントを秒・tick単位で記録する参照データです。録音波形上の音素境界を自動推定したものではありません。MIDIノート開始時刻と音声の発音開始時刻を同一視せず、音声/音素アラインメントは別工程で検証・手動修正する必要があります。TXT歌詞は文字単位、LRCは時刻ベースの近似割当てであり、日本語のモーラ/音素と音符の対応は手動確認が必要です。

## 既知の制約
譜面は簡易表示であり、出版譜相当の浄書ではありません。音価に基づく正確な符尾/連桁、休符の完全な記譜、タイ、付点、連符、調号、異名同音の文脈判定、拍子変更時の厳密な小節再構成は未実装です。録音機器の実動作は対象PCのマイク/ドライバーで確認してください。ヘッドホンを推奨します。


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
- Select a QC table row to show a red dashed cursor and zoom to the surrounding 1.5-second interval. Use **全体表示** to restore the full timeline.
- The on-screen table prioritizes actionable flags (low confidence, low RMS, large F0 jump). CSV output continues to include all frames and flags.


## P3.4 QC table markers

The QC frame list now shows visible symbols in its finding column: `× 大F0ジャンプ`, `○ 低信頼度`, `● 低RMS`, and `— F0未推定/無声音候補`. Row text color helps distinguish the finding type; combined findings use a separate color. The exported CSV keeps the original machine-readable flag values.
