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


## P1 の追加機能

### ベースライン音響特徴量の抽出

```powershell
.\.venv\Scripts\python.exe .\tools\extract_baseline_features.py .\RG_SingingAI_Dataset\raw\audio\S001_010001.wav
```

`log_mel`、`f0_hz`、`frame_times_sec`、およびシリアライズされた特徴量設定を含む圧縮NPZを出力します。自己相関F0推定器は意図的に**診断用ベースライン**として実装されており、本番用のピッチトラッカーではありません。音素アラインメントは行わず、歌唱音声の生成も行いません。

### グループを考慮したデータ分割

実行前に、各メタデータJSONに `group_id`、`phrase_id`、`song_id`、または `source_group_id` を追加してください。グループ化キーは、データセットの分割（パーティション）を跨いではならない最高レベルの共有音楽素材を識別する必要があります（個々のテイクよりも曲/フレーズ単位でのグループ化を推奨）。

```powershell
.\.venv\Scripts\python.exe .\tools\make_splits.py --metadata-dir .\RG_SingingAI_Dataset\metadata --output .\RG_SingingAI_Dataset\splits\split_manifest.json --seed 20261015 --group-key song_id
```

このツールは、グループ化メタデータが不足している場合、黙ってテイクを個別に分割するのではなくエラーで終了します。グループによってサイズが異なる可能性があるため、最終的なアイテムの割合は80/10/10から外れることがありますが、グループの整合性が優先されます。

### 評価用ヘルパー

`recording_tool.evaluation` は、有声参照/予測ペアに対する F0 RMSE/MAE および Gross Error Rate（大誤差率）、さらにミリ秒単位のオンセット MAE を提供します。これらの指標は信頼できる参照データを必要とし、推定された F0 やノート境界の正確性を自動的に確定するものではありません。聴感評価（リスニングテスト）が引き続き必要です。

## データメタデータの更新

分割のリーク（学習データと評価データの混同）を防ぐため、今後の録音には `group_id`、`phrase_id`、`song_id`、または `source_group_id` の少なくとも1つを含める必要があります。録音GUIには、song_id、phrase_id、group_id のオプションフィールドが用意されています。分割を生成する前に、関連するテイク間で同じグループ化キーを一貫して使用してください。


## P2 の追加機能
- P1の録音、楽譜、MIDI参照、QC、確定的なグループ分割、およびベースライン特徴量を保持しています。
- GUIでテイクのメタデータに `song_id`、`phrase_id`、`group_id` をオプションで収集できるようになり、リーク耐性のあるデータセット分割が可能になりました。テイク間で同じグループ化キーを一貫して使用してください。
- `tools/extract_baseline_features.py` は、P1の log-Mel / F0 に加えて、P2のスペクトルエンベロープ、HNRプロキシ、大まかなフォルマント推定値、非周期性、ブレス感、および声質プロキシアレイをNPZに出力するようになりました。
- P2記述子は診断用の近似値であり、校正されたグランドトゥルースではありません。MIDI/音声の強制アラインメントは保証されません。

### P2特徴量の抽出
```powershell
python tools/extract_baseline_features.py path\to\take.wav --output path\to\take.features_p2.npz
```


## P2.1 堅牢化と検証
- P1/P2の録音およびデータセット機能を維持しています。
- 特徴量抽出にはFFTベースの自己相関を使用し、放物線ラグ補間と明示的に未校正のF0信頼度プロキシを含みます。
- スペクトルエンベロープ推定にはケプストラム平滑化を使用し、フォルマントピーク強度プロキシは別途保存されます。
- 入力検証により、欠損、空、非モノラル、不適切なサンプルレート、および非有限値の音声を拒否します。数値出力は有限値と一貫したフレーム数について検査されます。
- NPZファイルは一時ファイルと原子的な置換を介して書き込まれます。`--overwrite` が指定されない限り、既存の出力は保護されます。
- フレームタイムスタンプは引き続きフレーム開始タイムスタンプであり、中心補正や音声/音素/MIDIのアラインメントは推論されません。
- すべての HNR/フォルマント/ブレス感/非周期性/声質の項目は診断用プロキシであり、グランドトゥルースとして扱わないでください。

### 抽出コマンド
```powershell
.\.venv\Scripts\python.exe .\tools\extract_baseline_features.py `
  ".\RG_SingingAI_Dataset\raw\audio\S001_010001.wav"
```
既存の出力を意図的に置換する場合は、`--overwrite` を追加してください。

### 自動テスト
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```


## P3.0 実験的研究モジュール

本リリースでは、実験的なアラインメントユーティリティ、オプションのWORLDベース音響分析、学習可能な音素/ピッチ条件付き log-mel ネットワーク、および Griffin-Lim レンダリングベースラインが追加されています。これらは研究用スキャフォールド（骨組み）であり、**完成した高品位歌唱合成器ではありません**。

### オプションのインストール（Windows / PowerShell）

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ml]"
# オプションの音響分析エクストラ（pyworld ホイールの利用可能性は Python/プラットフォームに依存します）:
.\.venv\Scripts\python.exe -m pip install -e ".[acoustic]"
```

### アラインメントドラフト

`phonemes.json` と `notes.json` を有効な JSON として準備します。例 `phonemes.json`:

```json
[{"label":"k"},{"label":"a"}]
```

例 `notes.json`:

```json
[{"start":0.0,"end":0.5,"pitch":60}]
```

次に以下を実行します：

```powershell
.\.venv\Scripts\python.exe .\tools\align_phonemes_midi.py --phonemes .\phonemes.json --notes .\notes.json --duration 0.5 --out .\alignment.json
```

音素のタイムスタンプが提供されない場合、境界はデュレーション分布の推測に過ぎず、`needs_manual_review` が true になります。これは音声条件付きの強制アラインメントではありません。

### 音響分析

```powershell
.\.venv\Scripts\python.exe -c "from recording_tool.singing.acoustic import analyze_world; import numpy as np; r=analyze_world('voice.wav'); np.savez_compressed('world_features.npz', **{k:v for k,v in r.items() if isinstance(v,np.ndarray)}); print(r['metadata'])"
```

WORLD F0 およびスペクトル特徴量はアルゴリズムによる推定値であり、校正された測定値ではありません。HNR およびフォルマント候補は参照ラベルとの検証が必要です。マイク/部屋の校正は実装されていません。

### ニューラル学習データの規約

各学習用 NPZ には、フレームアラインメントされたアレイ `log_mel[T,80]`、`phoneme_ids[T]`、`midi_pitch[T]`、および `velocity[T]` が含まれている必要があります。既存の P2 特徴量 NPZ には自動的に音素/MIDIフレームラベルが含まれるわけではありません。最初にアラインメントを作成/検証してください。欠損ラベルをゼロとして扱わないでください。

```powershell
.\.venv\Scripts\python.exe -m recording_tool.singing.train --data .\training_frames --vocab-size 128 --epochs 50 --out .\models\singing_melnet.pt
.\.venv\Scripts\python.exe .\tools\render_singing.py --model .\models\singing_melnet.pt --score .\score_frames.json --out .\generated.wav
```

現在のレンダラーは mel 逆変換 + Griffin-Lim を使用しており、通常バズ音やノイズを含んだ音になり、商用レベルのニューラルボコーダーではありません。このモデルはまだ、音価、音素の遷移、ビブラート、表現力豊かなタイミング、または歌手の個性を堅牢に学習しません。


## P3.1 データセットパイプライン

アノテーション形式、データセット生成、学習コマンド、制限事項については `docs/P3.1_DATASET_PIPELINE.md` を参照してください。データセット生成には査読済みの音素タイムスタンプが必要です。このツールは音響強制アライナーではありません。


## 特徴量 / F0 QC GUI（追加）
PowerShell で起動します：
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_feature_qc_gui.ps1
```
GUIでは、モノラル 44.1 kHz WAV の選択と NPZ への P1/P2 診断特徴量の抽出、既存 NPZ の読み込み、F0 / 信頼度プロキシ / RMS のプロット、低信頼度 / 低RMS / 隣接 F0 の大きな跳躍フレームのフラグ立て、フラグ付けされた行の検査、および QC テーブルの CSV へのエクスポートが可能です。閾値は編集可能です。元の NPZ 値は変更されず、自動ピッチ補正は適用されません。フラグは確認候補であり、エラーの証明ではありません。HNR / フォルマント / ブレス感 / 非周期性出力は引き続き診断用プロキシです。


## P3.3 QC 可視性の改善

- F0 プロット上の赤い `×` マーカーは、隣接する大きな F0 の跳躍を示します。
- 信頼度プロット上のオレンジ色の輪郭線付きの円は、低信頼度フレームを示します。
- RMS プロット上の赤い円は、低 RMS フレームを示します。
- QC テーブルの行を選択すると、赤の破線カーソルが表示され、周囲の 1.5 秒のインターバルにズームします。全体タイムラインに戻すには **全体表示** を使用します。
- 画面上のテーブルは、対応が必要なフラグ（低信頼度、低RMS、大きなF0跳躍）を優先的に表示します。エクスポートされる CSV には引き続きすべてのフレームとフラグが含まれます。


## P3.4 QC テーブルのマーカー

QC フレームリストの検出項目列に視覚的な記号が表示されるようになりました：`× 大F0ジャンプ`、`○ 低信頼度`、`● 低RMS`、`— F0未推定/無声音候補`。行のテキスト色により検出項目の種類を区別できます。複数の検出項目が重なる場合は別の色が使用されます。エクスポートされた CSV には、元の機械読取可能なフラグ値が保持されます。
