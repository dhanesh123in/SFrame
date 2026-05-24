import shutil
import uuid
from pathlib import Path

from app.config import get_settings


def data_root() -> Path:
    root = Path(get_settings().data_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def asset_dir(asset_id: str) -> Path:
    path = data_root() / "assets" / asset_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset_original_path(asset_id: str, ext: str = "") -> Path:
    suffix = ext if ext.startswith(".") else f".{ext}" if ext else ""
    return asset_dir(asset_id) / f"original{suffix}"


def asset_preview_path(asset_id: str) -> Path:
    return asset_dir(asset_id) / "preview.webp"


def asset_meta_path(asset_id: str) -> Path:
    return asset_dir(asset_id) / "meta.json"


def resolve_asset_file(asset_id: str, filename: str | None = None, mime_type: str | None = None) -> Path:
    """Resolve on-disk path for an asset; prefer DB filename extension."""
    if filename:
        ext = Path(filename).suffix
        if ext:
            candidate = asset_original_path(asset_id, ext)
            if candidate.exists():
                return candidate
    if mime_type:
        from app.services import raw_develop
        from app.services.image_io import ALLOWED_MIME

        ext = ALLOWED_MIME.get(mime_type) or raw_develop.RAW_EXT_BY_MIME.get(mime_type)
        if ext:
            candidate = asset_original_path(asset_id, ext)
            if candidate.exists():
                return candidate
    asset_path = asset_dir(asset_id)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset directory {asset_id} not found")
    for child in sorted(asset_path.iterdir()):
        if child.is_file() and child.name.startswith("original"):
            return child
    raise FileNotFoundError(f"No file for asset {asset_id}")


def new_asset_id() -> str:
    return str(uuid.uuid4())


def delete_asset_dir(asset_id: str) -> bool:
    path = asset_dir(asset_id)
    if not path.exists():
        return False
    shutil.rmtree(path, ignore_errors=True)
    return True


def delete_assets_storage(asset_ids: list[str]) -> int:
    removed = 0
    for aid in asset_ids:
        if delete_asset_dir(aid):
            removed += 1
    return removed
