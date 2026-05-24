#!/usr/bin/env bash
# Install PyTorch with CUDA 12.4 wheels (matches drivers reporting CUDA 12.x).
# Run from repo root after creating apps/api/.venv
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/apps/api/.venv"

if [[ ! -d "$VENV" ]]; then
  echo "Create venv first: cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python"

echo "Uninstalling existing torch..."
"$PIP" uninstall -y torch torchvision torchaudio 2>/dev/null || true

echo "Installing PyTorch (CUDA 12.4)..."
"$PIP" install torch torchvision --index-url https://download.pytorch.org/whl/cu124

echo "Reinstalling API package..."
"$PIP" install -e "$ROOT/apps/api"

echo ""
"$PYTHON" -c "
import torch
print('torch', torch.__version__)
print('cuda build', torch.version.cuda)
print('cuda available', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU', torch.cuda.get_device_name(0))
"
