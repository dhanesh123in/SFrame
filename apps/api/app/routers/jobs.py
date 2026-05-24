import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app import db
from app.config import get_settings
from app.schemas import JobResponse, UpscaleRequest
from app.worker import process_upscale_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_response(job: dict) -> JobResponse:
    settings = get_settings()
    base = settings.public_api_url.rstrip("/")
    result_url = None
    preview_url = None
    result_width = result_height = result_file_size = None
    input_width = input_height = None
    if job.get("asset_id"):
        inp = db.get_asset(job["asset_id"])
        if inp:
            input_width, input_height = inp["width"], inp["height"]
    if job.get("result_asset_id"):
        aid = job["result_asset_id"]
        result_url = f"{base}/api/v1/assets/{aid}/download"
        preview_url = f"{base}/api/v1/assets/{aid}/preview"
        res = db.get_asset(aid)
        if res:
            result_width = res["width"]
            result_height = res["height"]
            result_file_size = res["file_size"]
    opts = job.get("options") or {}
    result_filename = None
    if job.get("result_asset_id"):
        res_asset = db.get_asset(job["result_asset_id"])
        if res_asset:
            result_filename = res_asset["filename"]

    return JobResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job.get("progress") or 0,
        message=job.get("message"),
        output_format=opts.get("output_format"),
        result_asset_id=job.get("result_asset_id"),
        result_filename=result_filename,
        result_url=result_url,
        preview_url=preview_url,
        result_width=result_width,
        result_height=result_height,
        result_file_size=result_file_size,
        input_width=input_width,
        input_height=input_height,
        upscale_mode=opts.get("mode"),
        error=job.get("error"),
    )


@router.post("/upscale", response_model=JobResponse)
async def start_upscale(body: UpscaleRequest, background_tasks: BackgroundTasks) -> JobResponse:
    meta = db.get_asset(body.asset_id)
    if not meta:
        raise HTTPException(404, "Asset not found")

    long_edge = max(meta["width"], meta["height"])
    settings = get_settings()
    if long_edge > settings.max_sr_long_edge:
        raise HTTPException(
            400,
            f"Image long edge ({long_edge}px) exceeds {settings.max_sr_long_edge}px. Crop first.",
        )

    job_id = str(uuid.uuid4())
    from app.services.image_io import normalize_format

    fmt = normalize_format(body.output_format)
    if fmt not in ("png", "jpeg", "tiff"):
        raise HTTPException(400, "output_format must be png, jpeg, or tiff")
    mode = body.mode.lower()
    if mode not in ("aura", "faithful", "ultrasharp"):
        raise HTTPException(400, "mode must be aura, faithful, or ultrasharp")
    denoise = max(0.0, min(1.0, body.denoise_strength))
    weight = body.tile_weight_type.lower()
    if weight not in ("checkboard", "constant"):
        raise HTTPException(400, "tile_weight_type must be checkboard or constant")
    allowed_aura = ("fal/AuraSR-v2", "fal-ai/AuraSR")
    allowed_ultrasharp = ("Kim2091/UltraSharpV2", "Kim2091/UltraSharpV2-Lite")
    model_id = body.model_id
    if mode == "aura":
        model_id = model_id or get_settings().model_id
        if model_id not in allowed_aura:
            raise HTTPException(400, f"model_id must be one of {allowed_aura}")
    elif mode == "ultrasharp":
        model_id = model_id or "Kim2091/UltraSharpV2"
        if model_id not in allowed_ultrasharp:
            raise HTTPException(400, f"model_id must be one of {allowed_ultrasharp}")
    else:
        model_id = model_id or get_settings().model_id
    options = {
        "overlapping_tiles": body.overlapping_tiles,
        "upscale_factor": body.upscale_factor,
        "output_format": fmt,
        "mode": mode,
        "denoise_strength": denoise,
        "tile_weight_type": weight,
        "max_batch_size": body.max_batch_size,
        "model_id": model_id,
        "aura_seed": body.aura_seed,
    }
    db.insert_job(job_id, body.asset_id, options)
    background_tasks.add_task(process_upscale_job, job_id)
    job = db.get_job(job_id)
    return _job_response(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_response(job)
