import shutil
import uuid
from pathlib import Path

import exifread
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app import db
from app.config import get_settings
from app.schemas import AssetResponse, CropRequest, CropResponse
from app.services import crop, image_io, preview_live, raw_develop, storage

router = APIRouter(prefix="/assets", tags=["assets"])


def _preview_url(asset_id: str) -> str:
    settings = get_settings()
    return f"{settings.public_api_url.rstrip('/')}/api/v1/assets/{asset_id}/preview"


def _exif_summary(path: Path) -> str | None:
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        parts = []
        for key in (
            "Image Make",
            "Image Model",
            "EXIF LensModel",
            "EXIF FNumber",
            "EXIF ExposureTime",
            "EXIF ISOSpeedRatings",
        ):
            if key in tags:
                parts.append(f"{key.split()[-1]}: {tags[key]}")
        return " · ".join(parts[:6]) if parts else None
    except Exception:
        return None


@router.post("", response_model=AssetResponse)
async def upload_asset(file: UploadFile = File(...)) -> AssetResponse:
    settings = get_settings()
    if not file.filename:
        raise HTTPException(400, "Missing filename")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")

    raw_mime = raw_develop.detect_raw(content[:32], file.filename)
    mime = raw_mime or image_io.detect_mime(content[:16])

    if not mime:
        raise HTTPException(
            400,
            "Unsupported format. Use JPEG, PNG, TIFF, or Canon RAW (.cr2, .cr3).",
        )

    asset_id = storage.new_asset_id()

    if raw_mime:
        ext = raw_develop.RAW_EXT_BY_MIME[raw_mime]
        original_path = storage.asset_original_path(asset_id, ext)
        original_path.write_bytes(content)
        try:
            width, height, mime = raw_develop.validate_raw(original_path)
        except ValueError as exc:
            shutil.rmtree(storage.asset_dir(asset_id), ignore_errors=True)
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            shutil.rmtree(storage.asset_dir(asset_id), ignore_errors=True)
            raise HTTPException(400, f"Could not read RAW file: {exc}") from exc

        preview_path = storage.asset_preview_path(asset_id)
        try:
            preview_w, preview_h = raw_develop.write_preview(original_path, preview_path)
        except Exception as exc:
            shutil.rmtree(storage.asset_dir(asset_id), ignore_errors=True)
            raise HTTPException(400, f"Could not build RAW preview: {exc}") from exc

        kind = "raw"
    else:
        if mime not in image_io.ALLOWED_MIME:
            raise HTTPException(400, "Unsupported image format.")
        ext = image_io.ALLOWED_MIME[mime]
        original_path = storage.asset_original_path(asset_id, ext)
        original_path.write_bytes(content)
        try:
            width, height, mime = image_io.validate_image(original_path)
        except ValueError as exc:
            shutil.rmtree(storage.asset_dir(asset_id), ignore_errors=True)
            raise HTTPException(400, str(exc)) from exc

        preview_path = storage.asset_preview_path(asset_id)
        preview_w, preview_h = image_io.save_preview(original_path, preview_path)
        kind = "original"

    db.insert_asset(
        asset_id,
        kind=kind,
        filename=file.filename,
        mime_type=mime,
        width=width,
        height=height,
        file_size=len(content),
    )

    return AssetResponse(
        asset_id=asset_id,
        width=width,
        height=height,
        preview_width=preview_w,
        preview_height=preview_h,
        file_size=len(content),
        mime_type=mime,
        preview_url=_preview_url(asset_id),
        filename=file.filename,
        exif_summary=_exif_summary(original_path),
        kind=kind,
    )


@router.get("/{asset_id}/preview")
async def get_preview(asset_id: str) -> FileResponse:
    meta = db.get_asset(asset_id)
    if not meta:
        raise HTTPException(404, "Asset not found")
    preview = storage.asset_preview_path(asset_id)
    if not preview.exists():
        raise HTTPException(404, "Preview not found")
    return FileResponse(preview, media_type="image/webp")


@router.get("/{asset_id}/preview/live")
async def get_live_preview(
    asset_id: str,
    exposure: float = Query(0.0, ge=-1.0, le=1.0),
    contrast: float = Query(1.0, ge=0.5, le=1.5),
    saturation: float = Query(1.0, ge=0.0, le=2.0),
    brightness: float = Query(1.0, ge=0.5, le=1.5),
    temperature: float = Query(0.0, ge=-100.0, le=100.0),
    tint: float = Query(0.0, ge=-100.0, le=100.0),
    white_balance: str = Query("camera"),
) -> Response:
    meta = db.get_asset(asset_id)
    if not meta:
        raise HTTPException(404, "Asset not found")
    if white_balance not in ("camera", "auto"):
        raise HTTPException(400, "white_balance must be camera or auto")

    original = image_io.find_original_path(asset_id, meta.get("mime_type"))
    if not original:
        raise HTTPException(404, "Original file not found")

    is_raw = meta.get("kind") == "raw" or raw_develop.is_raw_mime(meta["mime_type"])
    preview_path = storage.asset_preview_path(asset_id)

    try:
        data = preview_live.render_live_preview(
            original=original,
            preview_path=preview_path,
            is_raw=is_raw,
            white_balance=white_balance,
            exposure=exposure,
            contrast=contrast,
            saturation=saturation,
            brightness=brightness,
            temperature=temperature,
            tint=tint,
        )
    except Exception as exc:
        raise HTTPException(500, f"Live preview failed: {exc}") from exc

    return Response(
        content=data,
        media_type="image/webp",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/{asset_id}/crop", response_model=CropResponse)
async def crop_asset(asset_id: str, body: CropRequest) -> CropResponse:
    meta = db.get_asset(asset_id)
    if not meta:
        raise HTTPException(404, "Asset not found")

    original = image_io.find_original_path(asset_id, meta.get("mime_type"))
    if not original:
        raise HTTPException(404, "Original file not found")

    if body.x + body.width > meta["width"] or body.y + body.height > meta["height"]:
        raise HTTPException(400, "Crop region exceeds image bounds")

    if body.white_balance not in ("camera", "auto"):
        raise HTTPException(400, "white_balance must be camera or auto")

    color_kw = dict(
        exposure=body.exposure,
        contrast=body.contrast,
        saturation=body.saturation,
        brightness=body.brightness,
        temperature=body.temperature,
        tint=body.tint,
    )

    cropped_id = storage.new_asset_id()
    stem = Path(meta["filename"]).stem
    is_raw = meta.get("kind") == "raw" or raw_develop.is_raw_mime(meta["mime_type"])

    if is_raw:
        dest = storage.asset_original_path(cropped_id, ".tiff")
        try:
            developed = raw_develop.develop_raw(
                original,
                white_balance=body.white_balance,
                temperature=body.temperature,
                tint=body.tint,
                exposure=body.exposure,
            )
            width, height = crop.apply_crop_image(
                developed,
                dest,
                x=body.x,
                y=body.y,
                width=body.width,
                height=body.height,
                rotate=body.rotate,
                flip_horizontal=body.flip_horizontal,
                flip_vertical=body.flip_vertical,
                output_mime="image/tiff",
                exposure=0.0,
                temperature=0.0,
                tint=0.0,
                contrast=body.contrast,
                saturation=body.saturation,
                brightness=body.brightness,
            )
        except Exception as exc:
            shutil.rmtree(storage.asset_dir(cropped_id), ignore_errors=True)
            raise HTTPException(500, f"RAW develop failed: {exc}") from exc
        out_mime = "image/tiff"
        cropped_name = f"{stem}_cropped.tiff"
    else:
        src_mime = meta["mime_type"]
        crop_ext = image_io.ALLOWED_MIME.get(src_mime, ".jpg")
        dest = storage.asset_original_path(cropped_id, crop_ext)
        width, height = crop.apply_crop(
            original,
            dest,
            x=body.x,
            y=body.y,
            width=body.width,
            height=body.height,
            rotate=body.rotate,
            flip_horizontal=body.flip_horizontal,
            flip_vertical=body.flip_vertical,
            output_mime=src_mime,
            **color_kw,
        )
        _, _, out_mime = image_io.validate_image(dest)
        cropped_name = f"{stem}_cropped{crop_ext}"

    preview_path = storage.asset_preview_path(cropped_id)
    image_io.save_preview(dest, preview_path)
    file_size = dest.stat().st_size

    db.insert_asset(
        cropped_id,
        kind="cropped",
        filename=cropped_name,
        mime_type=out_mime,
        width=width,
        height=height,
        file_size=file_size,
        parent_id=asset_id,
    )

    return CropResponse(
        cropped_asset_id=cropped_id,
        width=width,
        height=height,
        preview_url=_preview_url(cropped_id),
    )


@router.get("/{asset_id}/download")
async def download_asset(asset_id: str) -> FileResponse:
    meta = db.get_asset(asset_id)
    if not meta:
        raise HTTPException(404, "Asset not found")

    try:
        path = storage.resolve_asset_file(
            asset_id,
            filename=meta["filename"],
            mime_type=meta["mime_type"],
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

    return FileResponse(
        path,
        media_type=meta["mime_type"],
        filename=meta["filename"],
    )
