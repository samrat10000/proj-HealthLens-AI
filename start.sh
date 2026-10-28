#!/usr/bin/env bash
# HealthLens AI - start the app (macOS / Linux):  bash start.sh
cd "$(dirname "$0")/backend"
if [ ! -x .venv/bin/python ] || [ ! -f models/heart.joblib ]; then
  echo "The app is not set up yet. Run:  bash setup.sh"; exit 1
fi
URL="http://localhost:8501"
echo "Starting HealthLens AI at $URL  (press Ctrl+C to stop)"
( sleep 4; (command -v open >/dev/null && open "$URL") || (command -v xdg-open >/dev/null && xdg-open "$URL") ) >/dev/null 2>&1 &
.venv/bin/python -m streamlit run healthlens.py --server.address 127.0.0.1 --server.port 8501
