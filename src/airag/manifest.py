"""SQLite-based source manifest for tracking ingested files and chunks."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DDL = """\
CREATE TABLE IF NOT EXISTS sources (
    file_path       TEXT PRIMARY KEY,
    content_hash    TEXT NOT NULL,
    file_type       TEXT NOT NULL,
    ingested_at     TEXT NOT NULL,
    chunk_count     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        TEXT PRIMARY KEY,
    file_path       TEXT NOT NULL,
    qdrant_point_id TEXT NOT NULL,
    FOREIGN KEY (file_path) REFERENCES sources(file_path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
"""


def open_manifest(db_path: Path) -> sqlite3.Connection:
    """Open/create manifest DB, run DDL, enable WAL + foreign_keys."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_DDL)
    return conn


def get_source(conn: sqlite3.Connection, file_path: str) -> dict | None:
    """Return source row as dict for file_path, or None."""
    row = conn.execute(
        "SELECT file_path, content_hash, file_type, ingested_at, chunk_count "
        "FROM sources WHERE file_path = ?",
        (file_path,),
    ).fetchone()
    return dict(row) if row else None


def upsert_source(
    conn: sqlite3.Connection,
    file_path: str,
    content_hash: str,
    file_type: str,
    chunk_ids: list[str],
    qdrant_point_ids: list[str],
) -> None:
    """Record/update source after ingest."""
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("DELETE FROM chunks WHERE file_path = ?", (file_path,))
        conn.execute(
            "INSERT OR REPLACE INTO sources "
            "(file_path, content_hash, file_type, ingested_at, chunk_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (file_path, content_hash, file_type, now, len(chunk_ids)),
        )
        conn.executemany(
            "INSERT INTO chunks (chunk_id, file_path, qdrant_point_id) "
            "VALUES (?, ?, ?)",
            [
                (cid, file_path, pid)
                for cid, pid in zip(chunk_ids, qdrant_point_ids)
            ],
        )


def delete_source(conn: sqlite3.Connection, file_path: str) -> list[str]:
    """Delete source and return its qdrant_point_ids for Qdrant cleanup."""
    point_ids = [
        row[0]
        for row in conn.execute(
            "SELECT qdrant_point_id FROM chunks WHERE file_path = ?",
            (file_path,),
        ).fetchall()
    ]
    with conn:
        conn.execute("DELETE FROM sources WHERE file_path = ?", (file_path,))
    return point_ids


def list_stale_paths(
    conn: sqlite3.Connection, current_files: set[str]
) -> list[str]:
    """Return file_paths in manifest not present in current_files."""
    all_paths = [
        row[0]
        for row in conn.execute("SELECT file_path FROM sources").fetchall()
    ]
    return [p for p in all_paths if p not in current_files]
