$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
& "$root\backend\.venv\Scripts\python.exe" -m pytest "$root\backend"
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }
Push-Location "$root\frontend"
try {
  npm.cmd run test
  if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
  npm.cmd run build
  if ($LASTEXITCODE -ne 0) { throw "Frontend type-check or production build failed." }
}
finally { Pop-Location }
