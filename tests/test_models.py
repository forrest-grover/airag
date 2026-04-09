"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from airag.models import ChunkMetadata, ChunkResult, CorpusStats


class TestChunkMetadata:
    """Tests for ChunkMetadata model."""

    def test_valid_minimal(self):
        m = ChunkMetadata(
            chunk_id="abc123",
            file_path="/src/main.py",
            file_type="code",
            chunk_index=0,
            token_count=100,
        )
        assert m.chunk_id == "abc123"
        assert m.language is None
        assert m.symbol is None
        assert m.heading_path is None
        assert m.json_path is None

    def test_valid_full(self):
        m = ChunkMetadata(
            chunk_id="abc123",
            file_path="/src/main.py",
            file_type="code",
            language="python",
            symbol="my_func",
            heading_path=None,
            json_path=None,
            chunk_index=0,
            token_count=100,
        )
        assert m.language == "python"
        assert m.symbol == "my_func"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_id="abc",
                file_path="/a.py",
                # missing file_type
                chunk_index=0,
                token_count=10,
            )

    def test_wrong_type_chunk_index(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_id="abc",
                file_path="/a.py",
                file_type="code",
                chunk_index="not_an_int",
                token_count=10,
            )

    def test_wrong_type_token_count(self):
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_id="abc",
                file_path="/a.py",
                file_type="code",
                chunk_index=0,
                token_count="nope",
            )


class TestChunkResult:
    """Tests for ChunkResult model."""

    def test_valid(self):
        r = ChunkResult(
            chunk_id="abc123",
            score=0.95,
            file_path="/src/main.py",
            file_type="code",
            text="def hello(): pass",
        )
        assert r.score == 0.95
        assert r.language is None
        assert r.section is None

    def test_with_optional_fields(self):
        r = ChunkResult(
            chunk_id="abc123",
            score=0.8,
            file_path="/doc.md",
            file_type="markdown",
            language=None,
            symbol=None,
            heading_path="Intro > Setup",
            section="setup",
            text="Install steps...",
        )
        assert r.heading_path == "Intro > Setup"
        assert r.section == "setup"

    def test_missing_score(self):
        with pytest.raises(ValidationError):
            ChunkResult(
                chunk_id="abc",
                file_path="/a.py",
                file_type="code",
                text="content",
            )

    def test_missing_text(self):
        with pytest.raises(ValidationError):
            ChunkResult(
                chunk_id="abc",
                score=0.5,
                file_path="/a.py",
                file_type="code",
            )


class TestCorpusStats:
    """Tests for CorpusStats model."""

    def test_valid(self):
        s = CorpusStats(
            total_chunks=1000,
            total_sources=50,
            embedding_model="Qwen3-Embedding-0.6B",
            collection_name="airag",
        )
        assert s.total_chunks == 1000
        assert s.total_sources == 50

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            CorpusStats(
                total_chunks=100,
                # missing total_sources, embedding_model, collection_name
            )

    def test_negative_counts_allowed(self):
        """Pydantic int fields accept negative values by default."""
        s = CorpusStats(
            total_chunks=-1,
            total_sources=0,
            embedding_model="test",
            collection_name="test",
        )
        assert s.total_chunks == -1
