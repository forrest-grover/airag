"""Tests for SQLite manifest module."""

import sqlite3

import pytest

from airag.manifest import (
    delete_source,
    get_source,
    list_stale_paths,
    open_manifest,
    upsert_source,
)


@pytest.fixture
def db(tmp_path):
    """Open a manifest DB in a temp directory."""
    return open_manifest(tmp_path / "manifest.db")


class TestOpenManifest:
    def test_creates_tables(self, tmp_path):
        conn = open_manifest(tmp_path / "test.db")
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "sources" in tables
        assert "chunks" in tables
        conn.close()

    def test_foreign_keys_enabled(self, db):
        fk = db.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1

    def test_wal_mode(self, db):
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"


class TestUpsertAndGetSource:
    def test_upsert_and_get(self, db):
        upsert_source(db, "/a.py", "abc123", "code", ["c1", "c2"], ["10", "20"])
        src = get_source(db, "/a.py")
        assert src is not None
        assert src["file_path"] == "/a.py"
        assert src["content_hash"] == "abc123"
        assert src["file_type"] == "code"
        assert src["chunk_count"] == 2

    def test_replaces_old_chunks(self, db):
        upsert_source(db, "/a.py", "hash1", "code", ["c1", "c2"], ["10", "20"])
        upsert_source(db, "/a.py", "hash2", "code", ["c3"], ["30"])

        src = get_source(db, "/a.py")
        assert src["content_hash"] == "hash2"
        assert src["chunk_count"] == 1

        # Old chunks gone, only new chunk present
        rows = db.execute(
            "SELECT chunk_id FROM chunks WHERE file_path = ?", ("/a.py",)
        ).fetchall()
        assert [r[0] for r in rows] == ["c3"]


class TestDeleteSource:
    def test_returns_point_ids(self, db):
        upsert_source(db, "/a.py", "h", "code", ["c1", "c2"], ["10", "20"])
        ids = delete_source(db, "/a.py")
        assert sorted(ids) == ["10", "20"]
        assert get_source(db, "/a.py") is None

    def test_cascades_chunks(self, db):
        upsert_source(db, "/a.py", "h", "code", ["c1"], ["10"])
        delete_source(db, "/a.py")
        rows = db.execute(
            "SELECT * FROM chunks WHERE file_path = ?", ("/a.py",)
        ).fetchall()
        assert rows == []

    def test_nonexistent_returns_empty(self, db):
        assert delete_source(db, "/no/such/file.py") == []


class TestListStalePaths:
    def test_identifies_missing(self, db):
        upsert_source(db, "/a.py", "h", "code", ["c1"], ["1"])
        upsert_source(db, "/b.py", "h", "code", ["c2"], ["2"])
        upsert_source(db, "/c.py", "h", "code", ["c3"], ["3"])

        stale = list_stale_paths(db, {"/a.py", "/b.py"})
        assert stale == ["/c.py"]

    def test_no_stale(self, db):
        upsert_source(db, "/a.py", "h", "code", ["c1"], ["1"])
        assert list_stale_paths(db, {"/a.py"}) == []


class TestGetSourceNonexistent:
    def test_returns_none(self, db):
        assert get_source(db, "/nonexistent.py") is None
