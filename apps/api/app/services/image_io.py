import io
from pathlib import Path

from PIL import Image, ImageOps

from app.config import get_settings

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
}

EXT_TO_MIME = {v: k for k, v in ALLOWED_MIME.items()}

# All extensions we store under original.{ext}
ALL_STORAGE_EXTENSIONS = list(ALLOWED_MIME.values()) + [".cr2", ".cr3", ".crw"]


def detect_mime(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def find_original_path(asset_id: str, mime_type: str | None = None) -> Path | None:
    from app.services import raw_develop
    from app.services.storage import asset_dir, asset_original_path

    if mime_type and raw_develop.is_raw_mime(mime_type):
        ext = raw_develop.RAW_EXT_BY_MIME[mime_type]
        candidate = asset_original_path(asset_id, ext)
        if candidate.exists():
            return candidate

    for ext in ALL_STORAGE_EXTENSIONS:
        candidate = asset_original_path(asset_id, ext)
        if candidate.exists():
            return candidate

    asset_path = asset_dir(asset_id)
    if asset_path.exists():
        for child in sorted(asset_path.iterdir()):
            if child.is_file() and child.name.startswith("original"):
                return child
    return None


def open_image(path: Path) -> Image.Image:
    from app.services import raw_develop

    if raw_develop.is_raw_path(path):
        return raw_develop.develop_raw(path)
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def validate_image(path: Path) -> tuple[int, int, str]:
    from app.services import raw_develop

    if raw_develop.is_raw_path(path):
        return raw_develop.validate_raw(path)

    settings = get_settings()
    with open(path, "rb") as f:
        header = f.read(16)
    mime = detect_mime(header)
    if mime not in ALLOWED_MIME:
        raise ValueError(f"Unsupported image type: {mime}")

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        pixels = width * height
        if pixels > settings.max_pixels:
            raise ValueError(
                f"Image too large ({pixels:,} pixels). Max {settings.max_pixels:,}."
            )
        return width, height, mime


def save_preview(source: Path, dest: Path) -> tuple[int, int]:
    from app.services import raw_develop

    if raw_develop.is_raw_path(source):
        return raw_develop.write_preview(source, dest)

    settings = get_settings()
    img = open_image(source)
    w, h = img.size
    max_edge = settings.preview_max_edge
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="WEBP", quality=85, method=6)
    return img.size


def preview_dimensions(source: Path) -> tuple[int, int]:
    settings = get_settings()
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        w, h = img.size
    max_edge = settings.preview_max_edge
    if max(w, h) <= max_edge:
        return w, h
    scale = max_edge / max(w, h)
    return int(w * scale), int(h * scale)


def extension_for_format(fmt: str) -> str:
    fmt = fmt.lower()
    if fmt in ("png", "image/png"):
        return ".png"
    if fmt in ("tiff", "tif", "image/tiff"):
        return ".tiff"
    return ".jpg"


def mime_for_format(fmt: str) -> str:
    ext = extension_for_format(fmt)
    return EXT_TO_MIME.get(ext, "image/jpeg")


def normalize_format(fmt: str) -> str:
    f = fmt.lower().strip()
    if f.startswith("image/"):
        f = f.split("/")[-1]
    if f in ("jpg", "jpeg"):
        return "jpeg"
    if f in ("tif", "tiff"):
        return "tiff"
    if f == "png":
        return "png"
    return "png"


def save_image(
    img: Image.Image,
    path: Path,
    *,
    mime: str | None = None,
    format: str | None = None,
    quality: int | None = None,
) -> Path:
    settings = get_settings()
    path.parent.mkdir(parents=True, exist_ok=True)

    suffix_fmt = normalize_format(path.suffix.lstrip(".") or "png")
    fmt = normalize_format(format or mime or suffix_fmt)
    if path.suffix:
        fmt = suffix_fmt

    q = quality if quality is not None else settings.jpeg_quality

    if fmt == "png":
        if path.suffix.lower() != ".png":
            path = path.with_suffix(".png")
        img.save(path, format="PNG", compress_level=3)
    elif fmt == "tiff":
        if path.suffix.lower() not in (".tif", ".tiff"):
            path = path.with_suffix(".tiff")
        img.save(path, format="TIFF", compression="tiff_lzw")
    else:
        if path.suffix.lower() not in (".jpg", ".jpeg"):
            path = path.with_suffix(".jpg")
        img.save(
            path,
            format="JPEG",
            quality=q,
            subsampling=0,
            optimize=False,
        )
    return path
