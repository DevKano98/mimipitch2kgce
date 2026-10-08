# Local automation

- `setup.ps1` / `setup.sh`: create the Python environment, install dependencies, copy Excalidraw fonts, and create local data folders.
- `dev.ps1` / `dev.sh`: start FastAPI on port 8000 and Vite on port 5173; stopping the script stops both.
- `test.ps1` / `test.sh`: run backend tests, frontend tests, TypeScript checks, and the production build.

On Windows systems that block local PowerShell scripts, run them with
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/<name>.ps1`.
