#!/usr/bin/env bash
# Start SFrame with GPU API. Run from repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found"
  exit 1
fi

if ! docker info 2>/dev/null | grep -qi 'nvidia'; then
  if ! docker run --rm --runtime=nvidia nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
    echo "NVIDIA Container Toolkit is not configured for Docker."
    echo ""
    echo "Install it once:"
    echo "  sudo ./scripts/setup-nvidia-docker.sh"
    echo ""
    echo "Or run CPU-only:"
    echo "  docker compose up --build"
    exit 1
  fi
fi

echo "Starting SFrame with GPU (runtime: nvidia)..."
exec docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build "$@"
