from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.routers import assets, history, jobs
from app.services import upscale_local


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="SFrame API",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")


@app.get("/health")
async def health():
    diag = upscale_local.cuda_diagnostics()
    try:
        device = str(upscale_local._resolve_device())
    except RuntimeError as exc:
        device = f"error: {exc}"
    return {
        "status": "ok",
        "device": device,
        **diag,
    }


def run():
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8100, reload=True)
