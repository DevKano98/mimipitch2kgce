#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/backend/.venv/bin/python" -m pytest "$ROOT/backend"
(cd "$ROOT/frontend" && npm test && npm run build)
