#!/usr/bin/env bash
# HealthLens AI - one-time setup (macOS / Linux):  bash setup.sh
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "ERROR: Python 3.10+ is not installed. Get it from https://www.python.org/downloads/"; exit 1
fi
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "ERROR: Python 3.10 or newer is required (found $("$PY" --version))."; exit 1; }

cd backend
echo "[1/4] Creating a private Python environment (.venv)"
[ -d .venv ] || "$PY" -m venv .venv
echo "[2/4] Installing Python packages (1-3 minutes the first time)"
.venv/bin/python -m pip install --upgrade pip --quiet --disable-pip-version-check
.venv/bin/python -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo "[3/4] Training the AI models (about 1 minute)"
.venv/bin/python ml/download_data.py
.venv/bin/python -m ml.train
.venv/bin/python -m ml.samples
echo "[4/4] Preparing the website"
if [ -f "$ROOT/frontend/dist/index.html" ]; then
  echo "Website is already built - nothing to do."
elif command -v npm >/dev/null; then
  (cd "$ROOT/frontend" && npm install && npm run build)
else
  echo "ERROR: frontend/dist is missing and Node.js is not installed (https://nodejs.org)."; exit 1
fi
echo; echo "Setup complete! Now run:  bash start.sh"
