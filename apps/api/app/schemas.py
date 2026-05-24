from pydantic import BaseModel, Field


class AssetResponse(BaseModel):
    asset_id: str
    width: int
    height: int
    preview_width: int
    preview_height: int
    file_size: int
    mime_type: str
    preview_url: str
    filename: str
    exif_summary: str | None = None
    kind: str | None = None


class CropRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    rotate: int = Field(default=0, ge=0, le=360)
    flip_horizontal: bool = False
    flip_vertical: bool = False
    exposure: float = Field(default=0.0, ge=-1.0, le=1.0)
    contrast: float = Field(default=1.0, ge=0.5, le=1.5)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)
    brightness: float = Field(default=1.0, ge=0.5, le=1.5)
    temperature: float = Field(default=0.0, ge=-100.0, le=100.0)
    tint: float = Field(default=0.0, ge=-100.0, le=100.0)
    white_balance: str = Field(default="camera")


class CropResponse(BaseModel):
    cropped_asset_id: str
    width: int
    height: int
    preview_url: str


class UpscaleRequest(BaseModel):
    asset_id: str
    overlapping_tiles: bool = True
    upscale_factor: int = 4
    output_format: str = "png"
    mode: str = "ultrasharp"
    denoise_strength: float = 0.6
    tile_weight_type: str = "checkboard"
    max_batch_size: int = Field(default=8, ge=1, le=16)
    model_id: str | None = None
    aura_seed: int | None = 42


class HistoryAssetItem(BaseModel):
    asset_id: str
    parent_id: str | None = None
    kind: str
    filename: str
    mime_type: str
    width: int
    height: int
    file_size: int
    created_at: str
    preview_url: str


class HistoryJobSummary(BaseModel):
    job_id: str
    status: str
    upscale_mode: str | None = None
    output_format: str | None = None
    created_at: str
    message: str | None = None


class HistorySession(BaseModel):
    session_id: str
    created_at: str
    root: HistoryAssetItem
    cropped: HistoryAssetItem | None = None
    upscaled: HistoryAssetItem | None = None
    job: HistoryJobSummary | None = None


class HistoryListResponse(BaseModel):
    sessions: list[HistorySession]
    total: int
    limit: int
    offset: int


class DeleteAssetsRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1)


class DeleteAssetsResponse(BaseModel):
    deleted_asset_count: int
    deleted_storage_count: int
    deleted_ids: list[str]


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str | None = None
    output_format: str | None = None
    result_asset_id: str | None = None
    result_filename: str | None = None
    result_url: str | None = None
    preview_url: str | None = None
    result_width: int | None = None
    result_height: int | None = None
    result_file_size: int | None = None
    input_width: int | None = None
    input_height: int | None = None
    upscale_mode: str | None = None
    error: str | None = None
