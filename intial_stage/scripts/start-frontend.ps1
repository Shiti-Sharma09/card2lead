# CARD2LEAD - start the React dev server on http://localhost:5173
# (/api calls are proxied to the backend on port 8000)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location "$root\frontend"

if (-not (Test-Path node_modules)) {
  Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
  npm install
}

Write-Host "Frontend -> http://localhost:5173" -ForegroundColor Green
npm run dev
