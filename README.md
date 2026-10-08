# Slate

Slate is a local AI-native infinite canvas for learning. Paste or draw a problem, select the relevant work, and ask by text or voice. The tutor reads the canvas, verifies calculations with SymPy, and teaches by pointing, drawing, labelling, and speaking directly on the canvas.

## Run locally

Requirements: Python 3.12+, Node.js 20+, npm, and the two API keys documented in `.env.example`.

1. Copy `.env.example` to `.env` and add `GROQ_API_KEY` and `SARVAM_API_KEY`.
2. Install everything:
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1`
   - macOS/Linux: `./scripts/setup.sh`
3. Start Slate:
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/dev.ps1`
   - macOS/Linux: `./scripts/dev.sh`
4. Open `http://localhost:5173`.

The setup scripts create the Python environment, install both applications, copy Excalidraw's fonts for offline use, and create local SQLite/file storage. They are safe to run repeatedly. The canvas still opens without API keys; AI and voice features show a configuration message.

## Tests

- Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`
- macOS/Linux: `./scripts/test.sh`

The test scripts run pytest, Vitest, TypeScript checking, and a production Vite build. Provider calls are replaced with fakes in automated tests.

## Architecture

- `frontend/`: React 18, TypeScript, Vite, Tailwind, shadcn/Radix primitives, Excalidraw, Tesseract OCR, and browser audio.
- `backend/`: FastAPI, Pydantic, Groq orchestration, safety checks, sandboxed SymPy, Sarvam speech, SQLite, and local assets.
- `scripts/`: complete setup, development, and test automation for Windows and Unix-like systems.
- `docs/`: product, architecture, decisions, safety, testing, and implementation requirements.

API credentials stay in the root `.env`, which is git-ignored. The frontend uses only relative `/api` and `/ws` routes through Vite's development proxy.
