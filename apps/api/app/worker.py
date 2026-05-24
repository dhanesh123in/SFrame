import shutil
import uuid
from pathlib import Path

from app import db
from app.config import get_settings
from app.services import image_io, storage, upscale_local
from app.services.image_io import ALLOWED_MIME, normalize_format, open_image, save_image

def process_upscale_job(job_id: str) -> None:
    job = db.get_job(job_id)
    if not job:
        return

    asset_id = job["asset_id"]
    options = job.get("options") or {}
    overlapping_tiles = options.get("overlapping_tiles", True)
    settings = get_settings()
    output_format = normalize_format(
        options.get("output_format") or settings.upscale_output_format
    )
    mode = options.get("mode") or settings.default_upscale_mode
    denoise_strength = float(options.get("denoise_strength") or 0.0)
    tile_weight_type = options.get("tile_weight_type") or "checkboard"
    max_batch_size = int(options.get("max_batch_size") or settings.aura_default_batch_size)
    model_id = options.get("model_id") or settings.model_id
    aura_seed = options.get("aura_seed")
    if aura_seed is not None:
        aura_seed = int(aura_seed)
    ext = image_io.extension_for_format(output_format)

    try:
        db.update_job(job_id, status="running", progress=10, message="Preparing image")
        original = storage.asset_original_path(asset_id)
        if not original.exists():
            for mime, suffix in ALLOWED_MIME.items():
                candidate = storage.asset_original_path(asset_id, suffix)
                if candidate.exists():
                    original = candidate
                    break
            else:
                raise FileNotFoundError(f"Asset {asset_id} not found")

        def on_progress(pct: int, msg: str):
            db.update_job(job_id, progress=pct, message=msg)

        result_id = str(uuid.uuid4())
        result_path = storage.asset_dir(result_id) / f"original{ext}"

        upscale_local.run_local_upscale(
            original,
            mode=mode,
            overlapping_tiles=overlapping_tiles,
            tile_weight_type=tile_weight_type,
            max_batch_size=max_batch_size,
            model_id=model_id,
            aura_seed=aura_seed,
            denoise_strength=denoise_strength,
            output_format=output_format,
            output_path=result_path,
            on_progress=on_progress,
        )

        db.update_job(job_id, progress=85, message=f"Saving {output_format.upper()}")

        # Re-encode so on-disk bytes always match chosen format + extension
        img = open_image(result_path)
        result_path = save_image(img, result_path, format=output_format)

        width, height, mime = image_io.validate_image(result_path)
        preview_path = storage.asset_preview_path(result_id)
        image_io.save_preview(result_path, preview_path)

        stem = Path(db.get_asset(asset_id)["filename"]).stem if db.get_asset(asset_id) else asset_id[:8]
        out_name = f"{stem}_4x.{output_format}" if output_format != "jpeg" else f"{stem}_4x.jpg"

        db.insert_asset(
            result_id,
            kind="upscaled",
            filename=out_name,
            mime_type=mime,
            width=width,
            height=height,
            file_size=result_path.stat().st_size,
            parent_id=asset_id,
        )

        device_label = upscale_local._resolve_device().type
        mode_label = {
            "aura": "AuraSR",
            "ultrasharp": "UltraSharpV2",
            "faithful": "Lanczos",
        }.get(mode, mode)
        db.update_job(
            job_id,
            status="completed",
            progress=100,
            message=(
                f"Done — {mode_label} 4× on {device_label} "
                f"({width}×{height} {output_format.upper()})"
            ),
            result_asset_id=result_id,
        )
    except Exception as exc:
        db.update_job(
            job_id,
            status="failed",
            progress=0,
            error=str(exc),
            message="Failed",
        )
