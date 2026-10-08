$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" -WorkingDirectory "$root\backend" -PassThru -WindowStyle Hidden
$frontendExit = 0
try {
  Push-Location "$root\frontend"
  npm.cmd run dev
  $frontendExit = $LASTEXITCODE
}
finally {
  Pop-Location
  if (-not $backend.HasExited) { Stop-Process -Id $backend.Id }
}
if ($frontendExit -ne 0) { exit $frontendExit }
