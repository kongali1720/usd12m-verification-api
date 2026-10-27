#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
source scripts/env.sh
pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
sleep 1
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
