"""Tests for the ingestion pipeline (no Docker services required)."""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from airag.ingestion import file_hash, ingest, scan_directory, should_skip, SKIP_PATTERNS


# ---------------------------------------------------------------------------
# scan_directory
# ---------------------------------------------------------------------------


class TestScanDirectory:
    def test_skips_hidden_files(self, tmp_path):
        (tmp_path / "visible.py").write_text("code")
        (tmp_path / ".hidden").write_text("secret")
        files = scan_directory(tmp_path)
        names = [f.name for f in files]
        assert "visible.py" in names
        assert ".hidden" not in names

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".secret_dir"
        hidden.mkdir()
        (hidden / "file.py").write_text("code")
        (tmp_path / "top.py").write_text("code")
        files = scan_directory(tmp_path)
        names = [f.name for f in files]
        assert "top.py" in names
        assert "file.py" not in names

    def test_skips_binary_extensions(self, tmp_path):
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "code.py").write_text("pass")
        files = scan_directory(tmp_path)
        names = [f.name for f in files]
        assert "code.py" in names
        assert "image.png" not in names

    def test_skips_empty_files(self, tmp_path):
        (tmp_path / "empty.py").write_text("")
        (tmp_path / "notempty.py").write_text("x")
        files = scan_directory(tmp_path)
        names = [f.name for f in files]
        assert "notempty.py" in names
        assert "empty.py" not in names


# ---------------------------------------------------------------------------
# file_hash
# ---------------------------------------------------------------------------


class TestFileHash:
    def test_changes_on_modification(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("original")
        h1 = file_hash(f)

        # Ensure mtime changes (some filesystems have 1s resolution)
        time.sleep(0.05)
        f.write_text("modified content that is different")
        # Force different mtime
        os.utime(f, (time.time() + 1, time.time() + 1))
        h2 = file_hash(f)
        assert h1 != h2

    def test_deterministic(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("stable")
        assert file_hash(f) == file_hash(f)


# ---------------------------------------------------------------------------
# should_skip / SKIP_PATTERNS
# ---------------------------------------------------------------------------


class TestShouldSkip:
    def test_skip_patterns_match(self, tmp_path):
        for name in ["__pycache__", "node_modules", ".venv", ".git", "build"]:
            d = tmp_path / name
            d.mkdir(exist_ok=True)
            assert should_skip(d), f"Expected {name} to be skipped"

    def test_normal_dir_not_skipped(self, tmp_path):
        d = tmp_path / "src"
        d.mkdir()
        assert not should_skip(d)

    def test_egg_info_glob(self, tmp_path):
        d = tmp_path / "mypackage.egg-info"
        d.mkdir()
        assert should_skip(d)

    def test_allowed_dotfiles(self, tmp_path):
        for name in [".gitignore", ".dockerignore", ".editorconfig"]:
            f = tmp_path / name
            f.write_text("content")
            assert not should_skip(f), f"Expected {name} to NOT be skipped"


# ---------------------------------------------------------------------------
# ingest() with mocked services
# ---------------------------------------------------------------------------


def _make_mock_qdrant():
    """Build a mock QdrantClient with required methods."""
    mock = MagicMock()
    mock.get_collections.return_value.collections = []
    return mock


def _make_mock_embed(dimension=1024):
    """Return a side_effect function for embed_batch."""
    def _embed(texts, embed_url, client):
        return [[0.1] * dimension for _ in texts]
    return _embed


class TestIngestWithManifest:
    @patch("airag.ingestion.QdrantClient")
    @patch("airag.ingestion.embed_batch")
    def test_creates_manifest_entries(self, mock_embed, mock_qcls, tmp_path):
        mock_qcls.return_value = _make_mock_qdrant()
        mock_embed.side_effect = _make_mock_embed()

        # Create a small corpus
        (tmp_path / "a.txt").write_text("Hello world, this is file a.")
        (tmp_path / "b.txt").write_text("Goodbye world, this is file b.")

        ingest(corpus_dir=tmp_path, batch_size=8)

        # Verify manifest DB was created
        from airag.manifest import get_source, open_manifest

        db_path = tmp_path / ".airag_manifest.db"
        assert db_path.exists()

        conn = open_manifest(db_path)
        src_a = get_source(conn, str(tmp_path / "a.txt"))
        src_b = get_source(conn, str(tmp_path / "b.txt"))
        assert src_a is not None
        assert src_b is not None
        assert src_a["chunk_count"] > 0
        assert src_b["chunk_count"] > 0
        conn.close()

    @patch("airag.ingestion.QdrantClient")
    @patch("airag.ingestion.embed_batch")
    def test_skips_unchanged_files(self, mock_embed, mock_qcls, tmp_path):
        mock_qcls.return_value = _make_mock_qdrant()
        mock_embed.side_effect = _make_mock_embed()

        (tmp_path / "a.txt").write_text("Stable content.")

        # First ingest
        ingest(corpus_dir=tmp_path, batch_size=8)
        first_call_count = mock_embed.call_count

        # Second ingest -- file unchanged, should skip
        ingest(corpus_dir=tmp_path, batch_size=8)
        assert mock_embed.call_count == first_call_count  # no new embed calls


class TestDeleteMissing:
    @patch("airag.ingestion.QdrantClient")
    @patch("airag.ingestion.embed_batch")
    def test_removes_stale_source(self, mock_embed, mock_qcls, tmp_path):
        mock_client = _make_mock_qdrant()
        mock_qcls.return_value = mock_client
        mock_embed.side_effect = _make_mock_embed()

        # Create 3 files and ingest
        for name in ["a.txt", "b.txt", "c.txt"]:
            (tmp_path / name).write_text(f"Content of {name}")

        ingest(corpus_dir=tmp_path, batch_size=8)

        # Remove one file
        (tmp_path / "c.txt").unlink()

        # Re-ingest with delete_missing
        ingest(corpus_dir=tmp_path, batch_size=8, delete_missing=True)

        # Verify stale source removed from manifest
        from airag.manifest import get_source, open_manifest

        conn = open_manifest(tmp_path / ".airag_manifest.db")
        assert get_source(conn, str(tmp_path / "a.txt")) is not None
        assert get_source(conn, str(tmp_path / "b.txt")) is not None
        assert get_source(conn, str(tmp_path / "c.txt")) is None
        conn.close()

        # Verify qdrant delete was called for the stale points
        mock_client.delete.assert_called()
