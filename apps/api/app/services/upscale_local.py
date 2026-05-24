import json
import logging
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path

import torch
from PIL import Image, ImageFilter

from app.config import get_settings
from app.services.image_io import extension_for_format, normalize_format, open_image, save_image

logger = logging.getLogger(__name__)

_model = None
_model_id_loaded: str | None = None
_device: torch.device | None = None


def cuda_diagnostics() -> dict:
    info: dict = {
        "cuda_available": torch.cuda.is_available(),
        "torch_version": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    if torch.cuda.is_available():
        info["gpu_name"] = torch.cuda.get_device_name(0)
    else:
        try:
            count = torch.cuda.device_count()
            if count > 0:
                info["note"] = (
                    f"GPUs detected ({count}) but CUDA runtime unavailable. "
                    "PyTorch CUDA build may not match your NVIDIA driver. "
                    "Run: ./scripts/install-gpu-torch.sh"
                )
        except Exception as exc:
            info["note"] = str(exc)
    return info


def _resolve_device() -> torch.device:
    global _device
    if _device is not None:
        return _device

    settings = get_settings()
    if settings.device == "cpu":
        _device = torch.device("cpu")
    elif settings.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "DEVICE=cuda but CUDA is not available. "
                f"{cuda_diagnostics().get('note', 'Install GPU PyTorch: ./scripts/install-gpu-torch.sh')}"
            )
        _device = torch.device("cuda")
    else:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if _device.type == "cpu":
            diag = cuda_diagnostics()
            logger.warning(
                "AuraSR using CPU — CUDA unavailable. %s",
                diag.get("note", "See scripts/install-gpu-torch.sh"),
            )
    return _device


def _load_aura_sr(model_id: str):
    from aura_sr import AuraSR
    from huggingface_hub import snapshot_download
    from safetensors.torch import load_file

    device = str(_resolve_device())
    hf_model_path = Path(snapshot_download(model_id))
    config = json.loads((hf_model_path / "config.json").read_text())
    model = AuraSR(config, device=device)
    checkpoint = load_file(hf_model_path / "model.safetensors")
    model.upsampler.load_state_dict(checkpoint, strict=True)
    model.upsampler.eval()
    return model


def _get_model(model_id: str | None = None):
    global _model, _model_id_loaded
    settings = get_settings()
    mid = model_id or settings.model_id
    if _model is None or _model_id_loaded != mid:
        _model = _load_aura_sr(mid)
        _model_id_loaded = mid
    return _model


def preload_model() -> None:
    _get_model()


def upscale_faithful(img: Image.Image, scale: int = 4) -> Image.Image:
    w, h = img.size
    return img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)


def apply_denoise(img: Image.Image, strength: float) -> Image.Image:
    """Blend original with a mild smooth (0 = off, 1 = max). Reduces GAN grain."""
    if strength <= 0:
        return img
    strength = min(1.0, strength)
    smoothed = img.filter(ImageFilter.SMOOTH_MORE)
    if strength >= 1.0:
        return smoothed
    return Image.blend(img, smoothed, strength)


def _run_aura(
    img: Image.Image,
    *,
    overlapping_tiles: bool,
    tile_weight_type: str = "checkboard",
    max_batch_size: int = 8,
    model_id: str | None = None,
    aura_seed: int | None = 42,
) -> Image.Image:
    model = _get_model(model_id)
    device = _resolve_device()

    if aura_seed is not None:
        torch.manual_seed(aura_seed)
        if device.type == "cuda":
            torch.cuda.manual_seed_all(aura_seed)

    weight = tile_weight_type if tile_weight_type in ("checkboard", "constant") else "checkboard"
    batch = max(1, min(16, max_batch_size))

    if overlapping_tiles:
        return model.upscale_4x_overlapped(img, max_batch_size=batch, weight_type=weight)
    return model.upscale_4x(img, max_batch_size=batch)


def run_local_upscale(
    local_path: Path,
    *,
    mode: str = "aura",
    overlapping_tiles: bool = True,
    tile_weight_type: str = "checkboard",
    max_batch_size: int = 8,
    model_id: str | None = None,
    aura_seed: int | None = 42,
    denoise_strength: float = 0.0,
    output_format: str | None = None,
    output_path: Path | None = None,
    on_progress: Callable[[int, str], None] | None = None,
) -> Path:
    settings = get_settings()
    fmt = normalize_format(output_format or settings.upscale_output_format)
    ext = extension_for_format(fmt)
    img = open_image(local_path)
    w, h = img.size
    long_edge = max(w, h)

    if long_edge > settings.max_sr_long_edge:
        raise ValueError(
            f"Long edge {long_edge}px exceeds limit ({settings.max_sr_long_edge}px). "
            "Crop to a smaller region before upscaling."
        )

    upscale_mode = mode if mode in ("aura", "faithful", "ultrasharp") else "aura"

    if upscale_mode == "faithful":
        if on_progress:
            on_progress(40, "4× Lanczos resize (faithful, no AI grain)")
        result = upscale_faithful(img, scale=4)
    elif upscale_mode == "ultrasharp":
        from app.config import get_settings as gs
        from app.services import upscale_ultrasharp

        settings = gs()
        variant = "lite" if model_id and "lite" in model_id.lower() else "full"
        device = _resolve_device()
        if on_progress:
            gpu = torch.cuda.get_device_name(0) if device.type == "cuda" else None
            label = f"cuda ({gpu})" if gpu else device.type
            on_progress(30, f"UltraSharpV2 ({variant}) on {label}")
        if on_progress:
            on_progress(45, "UltraSharp 4× tiled inference…")
        tile_size = settings.ultrasharp_tile_size
        if not overlapping_tiles:
            tile_size = min(tile_size * 2, max(w, h))
        result = upscale_ultrasharp.upscale_image(
            img,
            variant=variant,
            tile_size=tile_size,
            tile_overlap=settings.ultrasharp_tile_overlap,
        )
        if denoise_strength > 0:
            if on_progress:
                on_progress(65, "Reducing grain…")
            result = apply_denoise(result, denoise_strength)
    else:
        device = _resolve_device()
        if on_progress:
            gpu = torch.cuda.get_device_name(0) if device.type == "cuda" else None
            label = f"cuda ({gpu})" if gpu else device.type
            on_progress(30, f"AuraSR-v2 on {label}")
        if on_progress:
            on_progress(
                45,
                "AuraSR 4× (GAN — may add texture on clean DSLR files)",
            )
        result = _run_aura(
            img,
            overlapping_tiles=overlapping_tiles,
            tile_weight_type=tile_weight_type,
            max_batch_size=max_batch_size,
            model_id=model_id,
            aura_seed=aura_seed,
        )
        if denoise_strength > 0:
            if on_progress:
                on_progress(65, "Reducing grain…")
            result = apply_denoise(result, denoise_strength)

    if not isinstance(result, Image.Image):
        result = Image.fromarray(result)

    rw, rh = result.size
    expected = (w * 4, h * 4)
    if (rw, rh) != expected:
        raise RuntimeError(
            f"Upscale output {rw}×{rh} does not match expected 4× input {w}×{h} → {expected[0]}×{expected[1]}"
        )

    if upscale_mode == "aura":
        result = result.filter(ImageFilter.UnsharpMask(radius=1.5, percent=110, threshold=2))
    elif upscale_mode == "ultrasharp":
        result = result.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=3))

    if on_progress:
        on_progress(75, "Encoding result")

    dest = output_path or Path(tempfile.mkdtemp()) / f"{uuid.uuid4()}_upscaled{ext}"
    return save_image(result, dest, format=fmt)
