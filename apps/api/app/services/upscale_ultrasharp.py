"""Kim2091/UltraSharpV2 4× upscaler via spandrel (DAT2)."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from spandrel import ImageModelDescriptor, ModelLoader

logger = logging.getLogger(__name__)

_model: ImageModelDescriptor | None = None
_variant_loaded: str | None = None

VARIANT_FILES = {
    "full": "4x-UltraSharpV2.safetensors",
    "lite": "4x-UltraSharpV2_Lite.safetensors",
}


def _resolve_device() -> torch.device:
    from app.services.upscale_local import _resolve_device as aura_device

    return aura_device()


def _download_weights(variant: str) -> Path:
    from huggingface_hub import hf_hub_download

    from app.config import get_settings

    settings = get_settings()
    filename = VARIANT_FILES.get(variant, VARIANT_FILES["full"])
    path = hf_hub_download(
        repo_id=settings.ultrasharp_repo_id,
        filename=filename,
    )
    return Path(path)


def _get_model(variant: str = "full") -> ImageModelDescriptor:
    global _model, _variant_loaded
    v = variant if variant in VARIANT_FILES else "full"
    if _model is None or _variant_loaded != v:
        device = _resolve_device()
        path = _download_weights(v)
        logger.info("Loading UltraSharpV2 (%s) from %s on %s", v, path, device)
        loader = ModelLoader(device=device)
        loaded = loader.load_from_file(str(path))
        if not isinstance(loaded, ImageModelDescriptor):
            raise RuntimeError(f"Expected image SR model, got {type(loaded)}")
        loaded.eval()
        _model = loaded
        _variant_loaded = v
    return _model


def preload_model(variant: str = "full") -> None:
    _get_model(variant)


def _pil_to_tensor(img: Image.Image, device: torch.device) -> torch.Tensor:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)


def _tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    out = tensor.squeeze(0).permute(1, 2, 0).clamp(0, 1).detach().cpu().numpy()
    return Image.fromarray((out * 255.0).round().astype(np.uint8))


def upscale_image(
    img: Image.Image,
    *,
    variant: str = "full",
    tile_size: int = 512,
    tile_overlap: int = 32,
) -> Image.Image:
    model = _get_model(variant)
    device = _resolve_device()
    scale = model.scale
    w, h = img.size

    if w <= tile_size and h <= tile_size:
        with torch.inference_mode():
            out = model(_pil_to_tensor(img, device))
        return _tensor_to_pil(out)

    out_w, out_h = w * scale, h * scale
    accum = np.zeros((out_h, out_w, 3), dtype=np.float32)
    weights = np.zeros((out_h, out_w), dtype=np.float32)
    stride = max(1, tile_size - tile_overlap)

    with torch.inference_mode():
        for y0 in range(0, h, stride):
            for x0 in range(0, w, stride):
                x1 = min(x0 + tile_size, w)
                y1 = min(y0 + tile_size, h)
                tx0 = max(0, x1 - tile_size)
                ty0 = max(0, y1 - tile_size)
                tile = img.crop((tx0, ty0, x1, y1))
                tout = model(_pil_to_tensor(tile, device))
                tile_np = tout.squeeze(0).permute(1, 2, 0).clamp(0, 1).cpu().numpy()

                ox, oy = tx0 * scale, ty0 * scale
                th, tw = tile_np.shape[0], tile_np.shape[1]
                wy = np.linspace(1.0, 1.0, th, dtype=np.float32)
                wx = np.linspace(1.0, 1.0, tw, dtype=np.float32)
                if tile_overlap > 0:
                    ramp = min(tile_overlap * scale, th // 2, tw // 2)
                    if ramp > 0:
                        r = np.linspace(0, 1, ramp, dtype=np.float32)
                        wy[:ramp] = r
                        wy[-ramp:] = r[::-1]
                        wx[:ramp] = r
                        wx[-ramp:] = r[::-1]
                w2d = np.outer(wy, wx)

                accum[oy : oy + th, ox : ox + tw] += tile_np * w2d[..., None]
                weights[oy : oy + th, ox : ox + tw] += w2d

    weights = np.maximum(weights, 1e-8)
    result = accum / weights[..., None]
    return Image.fromarray((result.clip(0, 1) * 255).astype(np.uint8))
