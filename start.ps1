# One-command start for Windows (PowerShell): sets up everything on first run, then launches Jarvis.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
  Write-Host "> Creating Python virtual environment..."
  py -3 -m venv .venv
}
$stamp = ".venv\.installed"
if (-not (Test-Path $stamp) -or (Get-Item backend\requirements.txt).LastWriteTime -gt (Get-Item $stamp).LastWriteTime) {
  Write-Host "> Installing backend packages..."
  .venv\Scripts\pip install -q -r backend\requirements.txt
  New-Item -ItemType File -Force $stamp | Out-Null
}
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "> Created .env - add your API key there or in Settings." }

if (-not (Test-Path frontend\node_modules)) {
  Write-Host "> Installing frontend packages..."
  Push-Location frontend; npm install --no-audit --no-fund; Pop-Location
}
if (-not (Test-Path frontend\dist)) {
  Write-Host "> Building the interface..."
  Push-Location frontend; npm run build; Pop-Location
}

Write-Host "> Starting Jarvis backend..."
$backend = Start-Process -FilePath .venv\Scripts\python.exe -ArgumentList "-m", "backend.main" -PassThru -WindowStyle Hidden
try {
  for ($i = 0; $i -lt 40; $i++) {
    try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/api/health | Out-Null; break } catch { Start-Sleep -Milliseconds 500 }
  }
  Write-Host "> Opening Jarvis..."
  Push-Location frontend; npx electron .; Pop-Location
} finally {
  Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
}
