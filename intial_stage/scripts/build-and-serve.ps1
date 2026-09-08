# CARD2LEAD - build the frontend and serve EVERYTHING from FastAPI on :8000.
# This is the setup to expose over one ngrok tunnel:  ngrok http 8000
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

# 1. build the frontend
Set-Location "$root\frontend"
if (-not (Test-Path node_modules)) {
  Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
  npm install
}
Write-Host "Building frontend..." -ForegroundColor Cyan
npm run build

# 2. prepare + run the backend (which now also serves frontend/dist)
Set-Location "$root\backend"
if (-not (Test-Path .venv)) {
  python -m venv .venv
}
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r requirements.txt
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "Created backend\.env - add GEMINI_API_KEY when you have it." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "App -> http://localhost:8000" -ForegroundColor Green
Write-Host "Expose it: open another terminal and run  ->  ngrok http 8000" -ForegroundColor Cyan
Write-Host ""
& $py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
