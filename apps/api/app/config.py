from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: str = "data"
    max_upload_mb: int = 250
    max_pixels: int = 120_000_000
    max_sr_long_edge: int = 4096
    preview_max_edge: int = 2048
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    public_api_url: str = "http://localhost:8100"
    model_id: str = "fal/AuraSR-v2"
    ultrasharp_repo_id: str = "Kim2091/UltraSharpV2"
    ultrasharp_tile_size: int = 512
    ultrasharp_tile_overlap: int = 32
    aura_default_batch_size: int = 8
    device: str = "auto"
    upscale_output_format: str = "png"
    jpeg_quality: int = 98  # only when output is jpeg; uses subsampling=0 (4:4:4)
    default_upscale_mode: str = "ultrasharp"


@lru_cache
def get_settings() -> Settings:
    return Settings()
