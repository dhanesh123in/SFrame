"""On-demand preview with color adjustments for the crop UI."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from app.config import get_settings
from app.services import image_io, raw_develop
from app.services.color_adjust import apply_color_adjust


def _needs_raw_redevelop(
    *,
    white_balance: str,
    temperature: float,
    tint: float,
    exposure: float,
) -> bool:
    return (
        white_balance == "auto"
        or temperature != 0
        or tint != 0
        or exposure != 0
    )


def render_live_preview(
    *,
    original: Path,
    preview_path: Path,
    is_raw: bool,
    white_balance: str = "camera",
    exposure: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    brightness: float = 1.0,
    temperature: float = 0.0,
    tint: float = 0.0,
) -> bytes:
    settings = get_settings()

    if is_raw and _needs_raw_redevelop(
        white_balance=white_balance,
        temperature=temperature,
        tint=tint,
        exposure=exposure,
    ):
        img = raw_develop.develop_raw_half(
            original,
            white_balance=white_balance,
            temperature=temperature,
            tint=tint,
            exposure=exposure,
        )
        pil_exposure = 0.0
        pil_temp = 0.0
        pil_tint = 0.0
    elif preview_path.exists():
        img = Image.open(preview_path).convert("RGB")
        pil_exposure = exposure
        pil_temp = temperature
        pil_tint = tint
    else:
        img = image_io.open_image(original)
        pil_exposure = exposure if not is_raw else 0.0
        pil_temp = temperature if not is_raw else 0.0
        pil_tint = tint if not is_raw else 0.0

    img = apply_color_adjust(
        img,
        exposure=pil_exposure,
        contrast=contrast,
        saturation=saturation,
        brightness=brightness,
        temperature=pil_temp,
        tint=pil_tint,
    )

    w, h = img.size
    max_edge = settings.preview_max_edge
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=86, method=4)
    return buf.getvalue()
