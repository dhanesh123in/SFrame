"""Canon RAW (CR2/CR3) ingest via LibRaw/rawpy."""

import io
import logging
from pathlib import Path

from PIL import Image

from app.config import get_settings
from app.services.image_io import open_image, save_preview

logger = logging.getLogger(__name__)

RAW_EXTENSIONS = {
    ".cr2": "image/x-canon-cr2",
    ".cr3": "image/x-canon-cr3",
    ".crw": "image/x-canon-crw",
}

RAW_EXT_BY_MIME = {v: k for k, v in RAW_EXTENSIONS.items()}


def is_raw_mime(mime: str) -> bool:
    return mime in RAW_EXT_BY_MIME


def is_raw_path(path: Path) -> bool:
    return path.suffix.lower() in RAW_EXTENSIONS


def detect_raw(header: bytes, filename: str | None) -> str | None:
    name = (filename or "").lower()
    ext = Path(name).suffix
    if ext in RAW_EXTENSIONS:
        return RAW_EXTENSIONS[ext]
    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in (b"crx ", b"CRX ", b"crx\x00"):
            return RAW_EXTENSIONS[".cr3"]
    if header[:4] in (b"II*\x00", b"MM\x00*") and ext in (".cr2", ".tif", ".tiff", ""):
        if ext == ".cr2" or name.endswith(".cr2"):
            return RAW_EXTENSIONS[".cr2"]
    return None


def read_dimensions(path: Path) -> tuple[int, int]:
    import rawpy

    with rawpy.imread(str(path)) as raw:
        return raw.sizes.width, raw.sizes.height


def write_preview(raw_path: Path, dest_webp: Path) -> tuple[int, int]:
    """Fast preview for crop UI — embedded JPEG thumb or half-size develop."""
    import rawpy

    dest_webp.parent.mkdir(parents=True, exist_ok=True)

    with rawpy.imread(str(raw_path)) as raw:
        try:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                img = Image.open(io.BytesIO(thumb.data))
                img = img.convert("RGB")
                tmp = dest_webp.with_suffix(".thumb.jpg")
                img.save(tmp, format="JPEG", quality=90)
                return save_preview(tmp, dest_webp)
            if thumb.format == rawpy.ThumbFormat.BITMAP:
                img = Image.fromarray(thumb.data).convert("RGB")
                tmp = dest_webp.with_suffix(".thumb.jpg")
                img.save(tmp, format="JPEG", quality=90)
                return save_preview(tmp, dest_webp)
        except rawpy.LibRawNoThumbnailError:
            logger.info("No embedded thumbnail for %s, using half-size develop", raw_path.name)

        rgb = raw.postprocess(
            use_camera_wb=True,
            half_size=True,
            no_auto_bright=False,
            output_bps=8,
        )
        img = Image.fromarray(rgb)
        tmp = dest_webp.with_suffix(".half.jpg")
        img.save(tmp, format="JPEG", quality=90)
        return save_preview(tmp, dest_webp)


def _postprocess_kwargs(
    *,
    white_balance: str = "camera",
    temperature: float = 0.0,
    tint: float = 0.0,
    exposure: float = 0.0,
    half_size: bool = False,
) -> dict:
    from app.services.color_adjust import raw_bright_factor, wb_multipliers

    post: dict = {
        "half_size": half_size,
        "no_auto_bright": False,
        "output_bps": 8,
    }
    wb = white_balance.lower()
    if wb == "auto":
        post["use_auto_wb"] = True
    elif temperature != 0 or tint != 0:
        post["user_wb"] = wb_multipliers(temperature, tint)
    else:
        post["use_camera_wb"] = True
    if exposure != 0:
        post["bright"] = raw_bright_factor(exposure)
    return post


def develop_raw(
    path: Path,
    *,
    white_balance: str = "camera",
    temperature: float = 0.0,
    tint: float = 0.0,
    exposure: float = 0.0,
) -> Image.Image:
    """Full-resolution RGB develop for crop/export (8-bit sRGB)."""
    import rawpy

    post = _postprocess_kwargs(
        white_balance=white_balance,
        temperature=temperature,
        tint=tint,
        exposure=exposure,
        half_size=False,
    )
    with rawpy.imread(str(path)) as raw:
        rgb = raw.postprocess(**post)
    return Image.fromarray(rgb)


def develop_raw_half(
    path: Path,
    *,
    white_balance: str = "camera",
    temperature: float = 0.0,
    tint: float = 0.0,
    exposure: float = 0.0,
) -> Image.Image:
    """Half-resolution develop for interactive live preview."""
    import rawpy

    post = _postprocess_kwargs(
        white_balance=white_balance,
        temperature=temperature,
        tint=tint,
        exposure=exposure,
        half_size=True,
    )
    with rawpy.imread(str(path)) as raw:
        rgb = raw.postprocess(**post)
    return Image.fromarray(rgb)


def validate_raw(path: Path) -> tuple[int, int, str]:
    settings = get_settings()
    mime = RAW_EXTENSIONS[path.suffix.lower()]
    width, height = read_dimensions(path)
    pixels = width * height
    if pixels > settings.max_pixels:
        raise ValueError(
            f"RAW image too large ({pixels:,} pixels). Max {settings.max_pixels:,}."
        )
    return width, height, mime
