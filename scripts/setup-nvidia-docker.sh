#!/usr/bin/env bash
# Install NVIDIA Container Toolkit so `docker compose` can use `gpus: all`.
# Ubuntu 22.04 / 24.04. Run: sudo ./scripts/setup-nvidia-docker.sh

set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo $0"
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found. Install NVIDIA drivers first, then re-run this script."
  exit 1
fi

echo "Host GPU:"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader

. /etc/os-release
case "${ID}-${VERSION_ID}" in
  ubuntu-22.04 | ubuntu-24.04 | debian-12)
    ;;
  *)
    echo "Unsupported OS: ${ID}-${VERSION_ID}. See https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
    ;;
esac

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L "https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list" \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update
apt-get install -y nvidia-container-toolkit

nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

echo ""
echo "Verifying GPU inside Docker (runtime: nvidia)..."
docker run --rm --runtime=nvidia nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

echo ""
echo "Done. From the sframe repo run:"
echo "  ./scripts/docker-up-gpu.sh"
echo "  # or: docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build"
