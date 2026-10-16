# RG Singing AI Recording Tool v1.0.0

Phase 0 Recording Protocol v1.0.0用のWindowsローカル録音ツール。

## 機能
- 44.1 kHz / 24-bit / mono PCM WAV原本保存
- 録音画面、クリック音、基準音、MIDI同期、歌詞表示
- Speaker / Session / Take管理と自動採番
- `S001_010001.wav`形式のstem命名
- MIDI / 歌詞 / metadata / QC JSONを同一stemで保存
- 録音後QC（形式、長さ、Peak、RMS、clipping検出）
- Audio Device一覧
- 入力WAVは加工しない

クリック/基準音はモニター出力だけでWAVには混ぜない。ヘッドホン推奨。

## 起動
PowerShell:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```
初回はPython 3.11のvenvと依存パッケージを自動作成します。

## 出力
```text
RG_SingingAI_Dataset/
├─ raw/audio/S001_010001.wav
├─ reference/midi/S001_010001.mid
├─ reference/lyrics/S001_010001.txt
├─ reference/metadata/S001_010001.json
└─ qc/S001_010001.json
```

自動G2P、forced alignment、F0/Mel/HNR/Formant等の特徴抽出はDataset Builder側で行う。
