# CARD2LEAD - runs every automated test and prints a plain summary.
# Usage:  .\scripts\test-all.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root 'backend\.venv\Scripts\python.exe'

if (-not (Test-Path $py)) {
  Write-Host "Backend not set up yet. Run  .\scripts\start-backend.ps1  once first." -ForegroundColor Red
  exit 1
}

$results = @()

function Run-Step($title, $scriptBlock) {
  Write-Host ""
  Write-Host ("-" * 60) -ForegroundColor DarkGray
  Write-Host "  $title" -ForegroundColor Cyan
  Write-Host ("-" * 60) -ForegroundColor DarkGray
  & $scriptBlock
  $ok = $?
  $script:results += [pscustomobject]@{ Step = $title; Passed = $ok }
  if ($ok) { Write-Host "  => OK" -ForegroundColor Green }
  else     { Write-Host "  => FAILED" -ForegroundColor Red }
}

Set-Location (Join-Path $root 'backend')

Run-Step "1. Code has no syntax errors"      { & $py -m compileall -q app }
Run-Step "2. App starts up cleanly"          { & $py -c "import app.main; print('   app loaded')" }
Run-Step "3. Offline tests (34 checks)"       { & $py tests\qa_offline.py }
Run-Step "4. Live tests (HEIC, concurrency, real Gemini)" { & $py tests\qa_live.py }
Run-Step "5. Sample cards - extraction quality" { & $py tests\sample_cards.py }

Set-Location (Join-Path $root 'frontend')
Run-Step "6. Web app builds" {
  if (-not (Test-Path node_modules)) { npm install --silent }
  npm run build
}

Set-Location $root
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor DarkGray
Write-Host "  SUMMARY" -ForegroundColor White
Write-Host ("=" * 60) -ForegroundColor DarkGray
foreach ($r in $results) {
  $mark = if ($r.Passed) { "[PASS]" } else { "[FAIL]" }
  $color = if ($r.Passed) { "Green" } else { "Red" }
  Write-Host ("  {0}  {1}" -f $mark, $r.Step) -ForegroundColor $color
}
$failed = ($results | Where-Object { -not $_.Passed }).Count
Write-Host ""
if ($failed -eq 0) { Write-Host "  All good. " -ForegroundColor Green }
else { Write-Host "  $failed step(s) failed - see the output above." -ForegroundColor Red }
