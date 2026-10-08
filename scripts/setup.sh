#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$ROOT/.env" ] || { cp "$ROOT/.env.example" "$ROOT/.env"; echo "Created .env. Add the two API keys when ready."; }
if [ ! -d "$ROOT/backend/.venv" ]; then
  python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else "Python 3.12 or newer is required.")'
  python3 -m venv "$ROOT/backend/.venv"
fi
"$ROOT/backend/.venv/bin/python" -m pip install -r "$ROOT/backend/requirements-dev.txt"
(cd "$ROOT/frontend" && npm install)
mkdir -p "$ROOT/frontend/public/fonts" "$ROOT/backend/data"
cp -R "$ROOT/frontend/node_modules/@excalidraw/excalidraw/dist/prod/fonts/." "$ROOT/frontend/public/fonts/"
echo "Setup complete. Empty API keys disable AI and voice without disabling the canvas."
