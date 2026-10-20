$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".\.venv\Scripts\python.exe")) { py -3 -m venv .venv }
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $python -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
& $python -c "import tkinter, numpy, sounddevice, soundfile, mido; print('Preflight: Python/Tkinter/NumPy/sounddevice/soundfile/mido OK')"
if ($LASTEXITCODE -ne 0) { throw "Preflight validation failed" }
& $python -m recording_tool
