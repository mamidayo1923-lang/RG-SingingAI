$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
Write-Host "=== RG Singing AI Recording Tool GUI v1.0.0 ===" -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher (py.exe) が見つかりません。Python 3.11/3.12 64-bit をインストールしてください。"
}
py -3 -m venv .venv
$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python -m PyInstaller --noconfirm --clean --windowed --name "RG_SingingAI_RecordingTool" --onedir --collect-all sounddevice --collect-all mido rg_recording_gui\__main__.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller のビルドに失敗しました。" }
Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host (Join-Path $Root "dist\RG_SingingAI_RecordingTool\RG_SingingAI_RecordingTool.exe")
Write-Host "配布するときは dist\RG_SingingAI_RecordingTool フォルダ全体をコピーしてください。"
