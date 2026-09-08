# CARD2LEAD - start the API in dev mode (auto-reload) on http://localhost:8000
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location "$root\backend"

if (-not (Test-Path .venv)) {
  Write-Host "Creating virtual environment..." -ForegroundColor Cyan
  python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r requirements.txt

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "Created backend\.env - add GEMINI_API_KEY when you have it (runs in mock mode until then)." -ForegroundColor Yellow
}

Write-Host "API -> http://localhost:8000  (docs at /docs)" -ForegroundColor Green
& $py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
