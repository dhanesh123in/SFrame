#!/usr/bin/env bash
# Start SFrame with CPU API (no GPU required).
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker compose up --build "$@"
