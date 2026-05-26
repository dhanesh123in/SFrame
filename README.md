# SFrame

Crop DSLR and Canon RAW images at full resolution, adjust color in a live preview, then upscale 4× locally on your GPU. Default enhancer is [UltraSharpV2](https://huggingface.co/Kim2091/UltraSharpV2); [AuraSR-v2](https://huggingface.co/fal/AuraSR-v2) and faithful Lanczos are also available.

## Features

- **Import** — JPEG, PNG, TIFF, Canon RAW (`.cr2`, `.cr3`)
- **Crop** — aspect ratios, rotate/flip, ⌘/Ctrl+scroll zoom, side-panel color & white balance with live preview
- **Enhance** — 4× UltraSharp v2 (default), AuraSR v1/v2, or Lanczos; tiled inference for large images
- **Export** — PNG / TIFF / JPEG download, before/after preview slider
- **History** — browse past sessions, download or delete assets (DB + on-disk files)

## Stack

| Layer | Tech |
|-------|------|
| Web | Next.js 15, TypeScript, Tailwind, react-advanced-cropper |
| API | FastAPI, Pillow, rawpy/LibRaw, spandrel, aura-sr, PyTorch |

## Requirements

- **GPU:** NVIDIA + CUDA recommended for upscaling
- **Local dev:** Python 3.10+, Node.js 20+
- **Docker GPU:** [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) + ~15GB free on `/` for images

## Data & model cache

| Path (host) | Purpose |
|-------------|---------|
| `./data/` | Uploads, crops, upscales, `jobs.db` |
| `./data/assets/<uuid>/` | `original.*`, `preview.webp` per asset |
| `./.cache/huggingface/` | UltraSharp, AuraSR weights (auto-download) |

Docker bind-mounts these same paths (see `docker-compose.yml`).

## Quick start (local — recommended)

```bash
chmod +x scripts/dev.sh scripts/install-gpu-torch.sh
./scripts/dev.sh
```

Or two terminals:

**API**

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp ../../.env.example ../../.env   # optional
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

**Web**

```bash
cd apps/web
npm install
API_URL=http://127.0.0.1:8100 npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The browser uses same-origin `/api/v1/*`; Next.js proxies to FastAPI (large uploads supported).

**GPU check:** [http://localhost:8100/health](http://localhost:8100/health) — `cuda_available` should be `true`. If not:

```bash
./scripts/install-gpu-torch.sh
# restart the API
```

**LAN:** use the machine IP, e.g. `http://192.168.1.50:3000` (not `localhost` on other devices).

## Docker

### GPU (after toolkit install)

```bash
sudo ./scripts/setup-nvidia-docker.sh   # once
chmod +x scripts/docker-up-gpu.sh scripts/docker-up.sh
./scripts/docker-up-gpu.sh
```

Same as:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

- Web: http://localhost:3000  
- API: http://localhost:8100 (health → `cuda_available: true`)  
- Verify: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec api python -c "import torch; print(torch.cuda.get_device_name(0))"`

Uses `runtime: nvidia` (not bare `gpus: all`) so Docker does not fail with `driver ""` when the toolkit is missing.

### CPU only (slow upscaling, no toolkit)

```bash
./scripts/docker-up.sh
# or: docker compose up --build
```

Plain `docker compose up` is **CPU-only** by design. For GPU, use `docker-up-gpu.sh`.

## Workflow

1. **Import** — upload; RAW keeps embedded preview for cropping  
2. **Crop** — region + optional color/WB; **Apply crop** runs full RAW develop → TIFF when needed  
3. **Enhance** — default **UltraSharp v2**, 60% grain reduction; or AuraSR / Lanczos  
4. **Export** — download upscaled file; compare previews (WebP, not full res)  
5. **History** — review or delete old sessions  

## Upscale modes

| Mode | Notes |
|------|--------|
| **UltraSharp v2** | Default. Strong detail via [Kim2091/UltraSharpV2](https://huggingface.co/Kim2091/UltraSharpV2) (CC BY-NC-SA 4.0). Full or Lite variant. |
| **AuraSR** | Softer GAN look; v2 is more DSLR-friendly. Overlapping tiles, optional denoise. |
| **Faithful** | Lanczos 4× only — no AI texture. |

Long edge max **4096 px** before upscale (crop tighter for larger sources).

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `data` | Assets + SQLite DB |
| `HF_HOME` | (system) | Hugging Face cache; Docker uses `/cache/huggingface` |
| `DEVICE` | `auto` | `cuda`, `cpu`, or `auto` |
| `DEFAULT_UPSCALE_MODE` | `ultrasharp` | `ultrasharp`, `aura`, `faithful` |
| `MODEL_ID` | `Kim2091/UltraSharpV2` | AuraSR HF id when mode is `aura` |
| `MAX_SR_LONG_EDGE` | `4096` | Reject upscale above this |
| `MAX_UPLOAD_MB` | `250` | Upload size limit |
| `API_URL` | `http://127.0.0.1:8100` | Next.js → FastAPI proxy (server-side) |
| `PUBLIC_API_URL` | `http://localhost:8100` | URLs returned in API responses |

Copy `.env.example` to `.env` at the repo root for local overrides.

## API (summary)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/assets` | Upload |
| GET | `/api/v1/assets/{id}/preview` | WebP preview |
| GET | `/api/v1/assets/{id}/preview/live` | Live color-adjust preview |
| POST | `/api/v1/assets/{id}/crop` | Crop + color settings |
| POST | `/api/v1/jobs/upscale` | Start 4× job |
| GET | `/api/v1/jobs/{id}` | Job status |
| GET | `/api/v1/assets/{id}/download` | Download file |
| GET | `/api/v1/history` | List processing sessions |
| DELETE | `/api/v1/history` | Delete assets (`{ "asset_ids": [...] }`) |

OpenAPI: [http://localhost:8100/docs](http://localhost:8100/docs)

## Canon RAW

1. **Upload** — stored as-is; fast thumb/half-size preview for the crop UI  
2. **Apply crop** — full develop + crop to TIFF (30–90s on large files)  
3. **Enhance** — same as other formats on the developed TIFF  

```bash
python -c "import rawpy; print('rawpy', rawpy.__version__)"
```

## Project layout

```
apps/api/          FastAPI, upscale workers, RAW develop
apps/web/          Next.js UI
data/              Runtime data (gitignored)
.cache/huggingface Model weights (gitignored)
scripts/           dev.sh, GPU torch, Docker helpers
docker-compose.yml CPU default
docker-compose.gpu.yml GPU overlay (runtime: nvidia)
```

## Tips

- Judge upscale quality on the **downloaded PNG at 100% zoom**, not only the export slider (previews are ~2048px WebP).  
- UltraSharp: compare cropped at 100% vs upscaled at 25% in Preview for matched scale.  
- Crop before upscaling — 4× VRAM and disk use grow quickly.  
- History delete removes DB rows and `data/assets/<id>/` folders (children included).
