#!/usr/bin/env bash
# Run API + web on /media/user/store1 (no Docker). Requires NVIDIA GPU for upscale.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DATA_DIR="${DATA_DIR:-$ROOT/data}"
export HF_HOME="${HF_HOME:-$ROOT/.cache/huggingface}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"
export PUBLIC_API_URL="${PUBLIC_API_URL:-http://localhost:8100}"
export DEVICE="${DEVICE:-auto}"

mkdir -p "$DATA_DIR" "$HF_HOME"

if [[ ! -d "$ROOT/apps/api/.venv" ]]; then
  echo "Creating API venv..."
  python3 -m venv "$ROOT/apps/api/.venv"
  "$ROOT/apps/api/.venv/bin/pip" install -e "$ROOT/apps/api"
fi

if [[ ! -d "$ROOT/apps/web/node_modules" ]]; then
  echo "Installing web deps..."
  (cd "$ROOT/apps/web" && npm install)
fi

trap 'kill 0' EXIT
"$ROOT/apps/api/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8100 --app-dir "$ROOT/apps/api" &
(cd "$ROOT/apps/web" && API_URL=http://127.0.0.1:8100 npm run dev) &
wait
