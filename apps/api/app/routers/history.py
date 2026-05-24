from fastapi import APIRouter, HTTPException, Query

from app import db
from app.schemas import DeleteAssetsRequest, DeleteAssetsResponse, HistoryListResponse
from app.services import history as history_service
from app.services import storage

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> HistoryListResponse:
    return history_service.list_history(limit=limit, offset=offset)


@router.delete("", response_model=DeleteAssetsResponse)
async def delete_history_assets(body: DeleteAssetsRequest) -> DeleteAssetsResponse:
    expanded = db.expand_with_descendants(body.asset_ids)
    if not expanded:
        raise HTTPException(404, "No matching assets found")

    db_count = db.delete_assets_and_jobs(body.asset_ids)
    storage_count = storage.delete_assets_storage(expanded)
    return DeleteAssetsResponse(
        deleted_asset_count=db_count,
        deleted_storage_count=storage_count,
        deleted_ids=expanded,
    )
