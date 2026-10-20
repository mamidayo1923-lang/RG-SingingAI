# RG Singing AI Recording Tool GUI v1.0.0

Windows 10/11 向けの白基調・ネオンブルーアクセントのデスクトップGUIです。GUIと録音処理を `rg_recording_gui/app.py` / `backend.py` に分離し、将来 RecordingTool 側を更新しやすい構成にしています。

## WindowsでEXEをビルド
1. Python 3.11 または 3.12 (64-bit) をインストールします。
2. ZIPを展開します。
3. PowerShellで展開先に移動し、実行します。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_exe.ps1
```

ビルド成果物:
`dist\RG_SingingAI_RecordingTool\RG_SingingAI_RecordingTool.exe`

`--onedir` ビルドなので、EXE単体ではなく `dist\RG_SingingAI_RecordingTool` フォルダ全体を使用・配布してください。初回ビルドにはインターネット接続が必要です（依存パッケージ取得）。

## ソースから実行
```powershell
.\run.ps1
```

## 実装済み
- 白基調・ブルーアクセントのデスクトップGUI
- 入力デバイス選択、44.1/48 kHz、モノラル 24-bit PCM WAV録音
- Speaker ID / Session ID / Take番号、WAVとJSONメタデータ保存
- MIDIノートの簡易表示、TXT/LRC歌詞ファイル読み込み、歌詞テキスト編集・保存
- 直近テイク一覧、録音経過時間、基本QCメタデータ

## 制限事項
- この環境はLinuxのため、Windows用EXEそのものはここではビルドしていません。`build_exe.ps1` をWindows PC上で実行してビルドします。
- クリック音・基準音・実時間レベルメーター・本格的な波形表示はUI上の準備表示のみで、まだ音声出力/解析処理には接続されていません。
- 楽譜は簡易プレビューで、拍子・調号・休符・タイ・連符・小節単位のページングなどの完全な楽譜組版には未対応です。
- 音声デバイスによる実録音、Windows EXEの起動テストはこの生成環境では未実施です。
- メタデータQCは基本情報のみで、ピーク/RMS/HNR等の本格的QCではありません。

## Backend integration
GUIから録音処理を分離しています。今後、既存 RecordingTool のAPIに合わせて `backend.py` の `RecordingBackend` を置き換えることで、画面デザインを維持したまま録音エンジンを更新できます。
