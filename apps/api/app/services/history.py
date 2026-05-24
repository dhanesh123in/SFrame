"""Build processing history sessions from DB rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app import db
from app.schemas import (
    HistoryAssetItem,
    HistoryJobSummary,
    HistoryListResponse,
    HistorySession,
)


def _client_preview_url(asset_id: str) -> str:
    return f"/api/v1/assets/{asset_id}/preview"


def _to_asset_item(row: dict[str, Any]) -> HistoryAssetItem:
    return HistoryAssetItem(
        asset_id=row["id"],
        parent_id=row.get("parent_id"),
        kind=row["kind"],
        filename=row["filename"],
        mime_type=row["mime_type"],
        width=row["width"],
        height=row["height"],
        file_size=row["file_size"],
        created_at=row["created_at"],
        preview_url=_client_preview_url(row["id"]),
    )


def _pick_job(jobs: list[dict[str, Any]]) -> HistoryJobSummary | None:
    if not jobs:
        return None
    job = jobs[0]
    opts = job.get("options") or {}
    return HistoryJobSummary(
        job_id=job["id"],
        status=job["status"],
        upscale_mode=opts.get("mode"),
        output_format=opts.get("output_format"),
        created_at=job["created_at"],
        message=job.get("message"),
    )


def list_history(*, limit: int = 50, offset: int = 0) -> HistoryListResponse:
    total = db.count_root_assets()
    roots = db.list_root_assets(limit=limit, offset=offset)
    all_assets = db.list_all_assets()
    by_parent: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for a in all_assets:
        by_parent[a.get("parent_id")].append(a)

    sessions: list[HistorySession] = []
    for root in roots:
        root_id = root["id"]
        children = by_parent.get(root_id, [])
        cropped = next((c for c in children if c["kind"] == "cropped"), None)
        upscaled = next((c for c in children if c["kind"] == "upscaled"), None)
        if cropped and not upscaled:
            upscaled = next(
                (c for c in by_parent.get(cropped["id"], []) if c["kind"] == "upscaled"),
                None,
            )

        tree_ids = [root_id]
        if cropped:
            tree_ids.append(cropped["id"])
        if upscaled:
            tree_ids.append(upscaled["id"])
        jobs = db.get_jobs_for_asset_ids(tree_ids)

        sessions.append(
            HistorySession(
                session_id=root_id,
                created_at=root["created_at"],
                root=_to_asset_item(root),
                cropped=_to_asset_item(cropped) if cropped else None,
                upscaled=_to_asset_item(upscaled) if upscaled else None,
                job=_pick_job(jobs),
            )
        )

    return HistoryListResponse(sessions=sessions, total=total, limit=limit, offset=offset)
