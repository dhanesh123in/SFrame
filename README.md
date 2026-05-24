# SFrame

DSLR image cropping and local AuraSR-v2 super-resolution. Upload JPEG/PNG/TIFF or **Canon RAW (.cr2, .cr3)**, crop at full resolution, then upscale 4× on your GPU with [fal/AuraSR-v2](https://huggingface.co/fal/AuraSR-v2).

## Stack

- **Web:** Next.js 15, TypeScript, Tailwind, react-advanced-cropper
- **API:** FastAPI, Pillow, **rawpy/LibRaw** (Canon RAW), aura-sr, PyTorch (CUDA)

## Requirements

- NVIDIA GPU with CUDA (recommended) or CPU (very slow)
- Python 3.11+
- Node.js 20+

## Quick start (recommended — no Docker)

Your project lives on `/media/user/store1` (plenty of space). Docker images land on `/` (often full). Use local dev:

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Or run API and web in two terminals (see below).

## Quick start (manual)

### API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp ../../.env.example ../../.env
uvicorn app.main:app --reload --port 8100
```

First upscale downloads the model from Hugging Face (~hundreds of MB).

Check GPU: [http://localhost:8100/health](http://localhost:8100/health) — `cuda_available` must be `true`.

If you see **cpu** but have an NVIDIA GPU, PyTorch likely mismatches your driver (e.g. `cu130` vs CUDA 12.8). Fix:

```bash
chmod +x scripts/install-gpu-torch.sh
./scripts/install-gpu-torch.sh
# restart the API
```

### Web

```bash
cd apps/web
npm install
API_URL=http://127.0.0.1:8100 npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The browser calls **`/api/v1/*` on the Next.js host** (same origin). A streaming route handler proxies to FastAPI using `API_URL` (supports uploads up to 150MB) — so you can test from another machine on your LAN without pointing the browser at port 8100.

**LAN testing:** on the GPU machine, find its IP (e.g. `192.168.1.50`), then from another device open `http://192.168.1.50:3000`. Do not use `localhost` on the remote device.

### Docker (GPU) — needs ~15GB+ free on `/`

**One-time: NVIDIA Container Toolkit** (fixes `could not select device driver "nvidia"`):

```bash
chmod +x scripts/setup-nvidia-docker.sh
sudo ./scripts/setup-nvidia-docker.sh
```

Then start with GPU (from repo root):

```bash
chmod +x scripts/docker-up-gpu.sh scripts/docker-up.sh
./scripts/docker-up-gpu.sh
```

Equivalent:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

- **API:** http://localhost:8100 — health must show `cuda_available: true`
- **Web:** http://localhost:3000
- **Data:** `./data/` · **Models:** `./.cache/huggingface/`

Verify GPU inside the API container:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec api python -c "import torch; print(torch.cuda.get_device_name(0))"
```

**CPU only** (no toolkit — upscaling is very slow):

```bash
./scripts/docker-up.sh
# or: docker compose up --build
```

Do **not** use plain `docker compose up` expecting GPU — the default compose file is CPU-only so it starts without the toolkit. Use `docker-up-gpu.sh` after setup.

If root disk is full: `docker system prune -af --volumes` then `df -h /`.

## Environment

| Variable | Description |
|----------|-------------|
| `MODEL_ID` | Hugging Face model id (default `fal/AuraSR-v2`) |
| `DEVICE` | `auto`, `cuda`, or `cpu` |
| `MAX_SR_LONG_EDGE` | Reject upscale if long edge exceeds this (default 4096) |
| `API_URL` | Server-side only: Next.js → FastAPI proxy target (default `http://127.0.0.1:8100`) |

## API

- `POST /api/v1/assets` — upload image
- `GET /api/v1/assets/{id}/preview` — downscaled preview
- `POST /api/v1/assets/{id}/crop` — full-res crop
- `POST /api/v1/jobs/upscale` — start local AuraSR job
- `GET /api/v1/jobs/{id}` — job status
- `GET /api/v1/assets/{id}/download` — download file

Docs: [http://localhost:8100/docs](http://localhost:8100/docs)

## Canon RAW (.cr2 / .cr3)

1. **Upload** — RAW is stored as-is; the crop UI uses a fast embedded preview (or half-size develop).
2. **Apply crop** — full-resolution develop + crop to TIFF (camera white balance). This step can take **30–90s** on large files.
3. **Enhance** — AuraSR or Lanczos runs on the developed TIFF like any other image.

Requires `rawpy` (LibRaw). After `pip install -e .`, verify with:

```bash
python -c "import rawpy; print('rawpy', rawpy.__version__)"
```

## Tips

- Crop large DSLR frames before upscaling; 4× output grows quickly and needs VRAM.
- Enable **Overlapping tiles** for fewer seams (slower).
- Use `DEVICE=cpu` only for small test images.
