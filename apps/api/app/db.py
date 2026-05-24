import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from app.config import get_settings


def _db_path() -> Path:
    settings = get_settings()
    path = Path(settings.data_dir) / "jobs.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                message TEXT,
                result_asset_id TEXT,
                error TEXT,
                options_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                kind TEXT NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                file_size INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_asset(
    asset_id: str,
    kind: str,
    filename: str,
    mime_type: str,
    width: int,
    height: int,
    file_size: int,
    parent_id: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO assets (id, parent_id, kind, filename, mime_type, width, height, file_size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (asset_id, parent_id, kind, filename, mime_type, width, height, file_size, _now()),
        )
        conn.commit()


def get_asset(asset_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        return dict(row) if row else None


def insert_job(job_id: str, asset_id: str, options: dict[str, Any]) -> None:
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, asset_id, status, progress, options_json, created_at, updated_at)
            VALUES (?, ?, 'pending', 0, ?, ?, ?)
            """,
            (job_id, asset_id, json.dumps(options), now, now),
        )
        conn.commit()


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    result_asset_id: str | None = None,
    error: str | None = None,
) -> None:
    fields: list[str] = ["updated_at = ?"]
    values: list[Any] = [_now()]
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)
    if message is not None:
        fields.append("message = ?")
        values.append(message)
    if result_asset_id is not None:
        fields.append("result_asset_id = ?")
        values.append(result_asset_id)
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    values.append(job_id)
    with _connect() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("options_json"):
            data["options"] = json.loads(data["options_json"])
        return data


def list_all_assets() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM assets ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def count_root_assets() -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM assets WHERE parent_id IS NULL"
        ).fetchone()
        return int(row["n"]) if row else 0


def list_root_assets(*, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM assets
            WHERE parent_id IS NULL
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def get_jobs_for_asset_ids(asset_ids: list[str]) -> list[dict[str, Any]]:
    if not asset_ids:
        return []
    placeholders = ",".join("?" * len(asset_ids))
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM jobs
            WHERE asset_id IN ({placeholders})
               OR result_asset_id IN ({placeholders})
            ORDER BY created_at DESC
            """,
            (*asset_ids, *asset_ids),
        ).fetchall()
        out = []
        for row in rows:
            data = dict(row)
            if data.get("options_json"):
                data["options"] = json.loads(data["options_json"])
            out.append(data)
        return out


def expand_with_descendants(asset_ids: list[str]) -> list[str]:
    """Return asset_ids plus all descendants (children, grandchildren)."""
    if not asset_ids:
        return []
    all_assets = list_all_assets()
    by_parent: dict[str, list[str]] = {}
    for a in all_assets:
        pid = a.get("parent_id")
        if pid:
            by_parent.setdefault(pid, []).append(a["id"])

    expanded: set[str] = set(asset_ids)
    queue = list(asset_ids)
    while queue:
        aid = queue.pop()
        for child_id in by_parent.get(aid, []):
            if child_id not in expanded:
                expanded.add(child_id)
                queue.append(child_id)
    return list(expanded)


def delete_assets_and_jobs(asset_ids: list[str]) -> int:
    if not asset_ids:
        return 0
    ids = expand_with_descendants(asset_ids)
    placeholders = ",".join("?" * len(ids))
    with _connect() as conn:
        conn.execute(
            f"DELETE FROM jobs WHERE asset_id IN ({placeholders}) OR result_asset_id IN ({placeholders})",
            (*ids, *ids),
        )
        cur = conn.execute(
            f"DELETE FROM assets WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()
        return cur.rowcount
