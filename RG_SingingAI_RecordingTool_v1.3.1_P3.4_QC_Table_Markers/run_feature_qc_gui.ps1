$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "仮想環境を作成します..."
    py -3 -m venv (Join-Path $PSScriptRoot ".venv")
    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}
Write-Host "依存関係を確認・インストールします..."
& $python -m pip install --upgrade pip
& $python -m pip install -e . matplotlib
if ($LASTEXITCODE -ne 0) { throw "依存関係のインストールに失敗しました。" }
Write-Host "特徴量・F0 QC GUIを起動します..."
& $python -m recording_tool.feature_qc_gui
if ($LASTEXITCODE -ne 0) { throw "GUIが異常終了しました。上記ログを確認してください。" }
