"""Pydantic models for airag."""

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""
    chunk_id: str
    file_path: str
    file_type: str
    language: str | None = None
    symbol: str | None = None
    heading_path: str | None = None
    json_path: str | None = None
    chunk_index: int
    token_count: int


class ChunkResult(BaseModel):
    """A chunk returned from search."""
    chunk_id: str
    score: float
    file_path: str
    file_type: str
    language: str | None = None
    symbol: str | None = None
    heading_path: str | None = None
    section: str | None = None
    text: str


class CorpusStats(BaseModel):
    """Corpus statistics."""
    total_chunks: int
    total_sources: int
    embedding_model: str
    collection_name: str
