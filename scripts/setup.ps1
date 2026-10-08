$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$root\.env")) { Copy-Item "$root\.env.example" "$root\.env"; Write-Host "Created .env. Add the two API keys when you are ready." }
if (-not (Test-Path "$root\backend\.venv")) {
  $launcher = Get-Command py -ErrorAction SilentlyContinue
  if ($launcher) {
    $version = & py -3 -c "import sys; print(sys.version_info >= (3, 12))"
    if ($version -ne "True") { throw "Python 3.12 or newer is required." }
    & py -3 -m venv "$root\backend\.venv"
  }
  else {
    $version = & python -c "import sys; print(sys.version_info >= (3, 12))"
    if ($version -ne "True") { throw "Python 3.12 or newer is required." }
    & python -m venv "$root\backend\.venv"
  }
}
& "$root\backend\.venv\Scripts\python.exe" -m pip install -r "$root\backend\requirements-dev.txt"
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed. Check your internet connection." }
Push-Location "$root\frontend"; try { npm.cmd install } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed. Check your internet connection." }
$fontSource = "$root\frontend\node_modules\@excalidraw\excalidraw\dist\prod\fonts"
if (Test-Path $fontSource) { New-Item -ItemType Directory -Force "$root\frontend\public\fonts" | Out-Null; Copy-Item "$fontSource\*" "$root\frontend\public\fonts" -Recurse -Force }
New-Item -ItemType Directory -Force "$root\backend\data" | Out-Null
$missing = Select-String -Path "$root\.env" -Pattern '^\s*(GROQ_API_KEY|SARVAM_API_KEY)\s*=\s*$'
if ($missing) { Write-Host "Setup complete. Add the missing API keys to .env for AI and voice." } else { Write-Host "Setup complete." }
