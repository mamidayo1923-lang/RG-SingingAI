param(
    [string]$Dataset = ".\RG_SingingAI_Dataset"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found."
    Write-Host "Run:"
    Write-Host "  py -3.11 -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

.\.venv\Scripts\python.exe -m rg_singing_ai_phase0 build `
    --dataset $Dataset `
    --config ".\config.yaml"
