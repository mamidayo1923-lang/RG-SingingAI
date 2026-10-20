# RG Singing AI Recording Tool v1.3.0

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

To prevent split leakage, future recordings should include at least one of `group_id`, `phrase_id`, `song_id`, or `source_group_id`. The recording GUI does not yet provide dedicated UI fields for these values; add them to metadata JSON or use a later GUI update before generating splits.
