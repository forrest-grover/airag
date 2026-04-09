"""Embedding smoke test: validates TEI produces correct vectors and applies asymmetric prompts.

Requires a running TEI instance serving Qwen3-Embedding-0.6B on TEI_EMBED_URL
(default http://localhost:8081). Tests are skipped when TEI is unreachable.
"""

import os

import httpx
import pytest

TEI_EMBED_URL = os.environ.get("TEI_EMBED_URL", "http://localhost:8081")
EXPECTED_DIMENSION = 1024


def _tei_reachable() -> bool:
    """Return True if TEI health endpoint responds."""
    try:
        resp = httpx.get(f"{TEI_EMBED_URL}/health", timeout=5.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


requires_tei = pytest.mark.skipif(
    not _tei_reachable(),
    reason=f"TEI not reachable at {TEI_EMBED_URL}",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _embed(text: str, prompt_name: str | None = None) -> list[float]:
    """Call the TEI embed endpoint for a single input."""
    payload: dict = {"inputs": text}
    if prompt_name is not None:
        payload["prompt_name"] = prompt_name
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{TEI_EMBED_URL}/embed", json=payload)
        resp.raise_for_status()
        return resp.json()[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@requires_tei
class TestEmbeddingSmoke:
    """Smoke tests for TEI embedding endpoint with Qwen3-Embedding-0.6B."""

    @pytest.mark.asyncio
    async def test_query_embedding_dimension(self):
        """Query embedding returns a vector of the expected dimensionality."""
        vec = await _embed("What is a fibonacci sequence?", prompt_name="query")
        assert isinstance(vec, list)
        assert len(vec) == EXPECTED_DIMENSION, (
            f"Expected {EXPECTED_DIMENSION}-d vector, got {len(vec)}-d"
        )

    @pytest.mark.asyncio
    async def test_document_embedding_dimension(self):
        """Document embedding (no prompt_name) returns correct dimensionality."""
        vec = await _embed("The Fibonacci sequence starts with 0 and 1.")
        assert isinstance(vec, list)
        assert len(vec) == EXPECTED_DIMENSION, (
            f"Expected {EXPECTED_DIMENSION}-d vector, got {len(vec)}-d"
        )

    @pytest.mark.asyncio
    async def test_asymmetric_prompts_differ(self):
        """Query and document embeddings of the same text must differ.

        Qwen3-Embedding-0.6B uses asymmetric prompts: queries get an
        instruction prefix while documents get none. If TEI is not applying
        the prompt template correctly, the vectors would be identical.
        """
        text = "Hybrid search combines dense and sparse retrieval."
        query_vec = await _embed(text, prompt_name="query")
        doc_vec = await _embed(text)

        assert len(query_vec) == EXPECTED_DIMENSION
        assert len(doc_vec) == EXPECTED_DIMENSION
        assert query_vec != doc_vec, (
            "Query and document embeddings are identical -- "
            "asymmetric prompt differentiation is not working"
        )

    @pytest.mark.asyncio
    async def test_embedding_values_are_finite(self):
        """Vectors should contain finite floats (no NaN/Inf from pooling bugs)."""
        import math

        vec = await _embed("simple test input", prompt_name="query")
        assert all(math.isfinite(v) for v in vec), (
            "Embedding contains non-finite values (NaN or Inf)"
        )
