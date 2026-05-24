"""Exposure / color adjustments applied before crop (Pillow + rawpy WB)."""

from __future__ import annotations

from PIL import Image, ImageEnhance


def wb_multipliers(temperature: float, tint: float) -> list[float]:
    """Map UI sliders (-100..100) to rawpy user_wb [R, G1, B, G2]."""
    t = max(-100.0, min(100.0, temperature)) / 100.0
    ti = max(-100.0, min(100.0, tint)) / 100.0
    r = max(0.25, 1.0 + t * 0.35)
    b = max(0.25, 1.0 - t * 0.35)
    g1 = max(0.25, 1.0 + ti * 0.2)
    g2 = max(0.25, 1.0 - ti * 0.15)
    return [r, g1, b, g2]


def raw_bright_factor(exposure: float) -> float:
    """Map exposure slider (-1..1) to rawpy bright."""
    e = max(-1.0, min(1.0, exposure))
    return max(0.35, min(3.0, 1.0 + e * 0.45))


def _apply_temp_tint(img: Image.Image, temperature: float, tint: float) -> Image.Image:
    if temperature == 0 and tint == 0:
        return img
    t = max(-100.0, min(100.0, temperature)) / 100.0
    ti = max(-100.0, min(100.0, tint)) / 100.0
    r, g, b = img.split()
    r = r.point(lambda i, f=1.0 + t * 0.18: min(255, int(i * f)))
    b = b.point(lambda i, f=1.0 - t * 0.18: min(255, int(i * f)))
    g = g.point(lambda i, f=1.0 + ti * 0.12: min(255, int(i * f)))
    return Image.merge("RGB", (r, g, b))


def apply_color_adjust(
    img: Image.Image,
    *,
    exposure: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    brightness: float = 1.0,
    temperature: float = 0.0,
    tint: float = 0.0,
) -> Image.Image:
    if exposure != 0:
        factor = 2 ** (max(-1.0, min(1.0, exposure)) * 0.5)
        img = ImageEnhance.Brightness(img).enhance(factor)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(max(0.25, min(2.5, brightness)))
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(max(0.25, min(2.5, contrast)))
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(max(0.0, min(2.5, saturation)))
    return _apply_temp_tint(img, temperature, tint)
