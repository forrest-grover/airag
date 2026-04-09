"""Qdrant search + rerank orchestration."""

import logging
import os

import httpx
from qdrant_client import QdrantClient

logger = logging.getLogger("airag")


class Retriever:
    """Handles embedding, search, and reranking."""

    def __init__(self):
        self._qdrant: QdrantClient | None = None
        self._qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        self._embed_url = os.environ.get("TEI_EMBED_URL", "http://localhost:8081")
        self._rerank_url = os.environ.get("TEI_RERANK_URL", "http://localhost:8082")
        self._collection = "corpus"
        self._embed_model = "Qwen/Qwen3-Embedding-0.6B"

    @property
    def qdrant(self) -> QdrantClient:
        if self._qdrant is None:
            self._qdrant = QdrantClient(url=self._qdrant_url)
        return self._qdrant

    async def embed(self, text: str) -> list[float]:
        """Embed a single text via TEI."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._embed_url}/embed",
                json={"inputs": text},
            )
            resp.raise_for_status()
            return resp.json()[0]

    async def search(
        self, query: str, k: int = 5, filters: dict | None = None
    ) -> list[dict]:
        """Embed query, search Qdrant, rerank, return top-k chunks."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        # 1. Embed query
        query_vector = await self.embed(query)

        # 2. Over-fetch from Qdrant for reranking
        fetch_k = min(k * 4, 20)

        qdrant_filter = None
        if filters:
            conditions: list[FieldCondition] = []
            for field, value in filters.items():
                conditions.append(
                    FieldCondition(key=field, match=MatchValue(value=value))
                )
            qdrant_filter = Filter(must=conditions)  # type: ignore[arg-type]

        results = self.qdrant.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=fetch_k,
            with_payload=True,
            query_filter=qdrant_filter,
        )

        if not results.points:
            return []

        # 3. Build chunk dicts from Qdrant results
        chunks = []
        for point in results.points:
            payload = point.payload or {}
            chunks.append(
                {
                    "chunk_id": payload.get("chunk_id", str(point.id)),
                    "score": point.score,
                    "file_path": payload.get("file_path", ""),
                    "file_type": payload.get("file_type", ""),
                    "language": payload.get("language"),
                    "symbol": payload.get("symbol"),
                    "heading_path": payload.get("heading_path"),
                    "section": payload.get("heading_path"),
                    "text": payload.get("text", ""),
                }
            )

        # 4. Try reranking, fall back to dense-only if reranker unavailable
        try:
            reranked = await self._rerank(query, chunks)
            chunks = reranked
        except Exception as e:
            logger.warning("Reranker unavailable, using dense scores: %s", e)

        # 5. Sort deterministically and return top-k
        chunks.sort(key=lambda c: (-c["score"], c["chunk_id"]))
        return chunks[:k]

    async def _rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """Rerank chunks via TEI reranker."""
        if not chunks:
            return chunks

        texts = [c["text"] for c in chunks]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._rerank_url}/rerank",
                json={"query": query, "texts": texts, "return_text": False},
            )
            resp.raise_for_status()

        scored = resp.json()
        for item in scored:
            idx = item["index"]
            chunks[idx]["score"] = item["score"]

        return chunks

    async def get_chunk(self, chunk_id: str) -> dict | None:
        """Fetch a single chunk by ID from Qdrant."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        results = self.qdrant.scroll(
            collection_name=self._collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))]
            ),
            limit=1,
            with_payload=True,
        )

        points, _ = results
        if not points:
            return None

        payload = points[0].payload or {}
        return {
            "chunk_id": payload.get("chunk_id", str(points[0].id)),
            "file_path": payload.get("file_path", ""),
            "file_type": payload.get("file_type", ""),
            "language": payload.get("language"),
            "symbol": payload.get("symbol"),
            "heading_path": payload.get("heading_path"),
            "token_count": payload.get("token_count"),
            "chunk_index": payload.get("chunk_index"),
            "text": payload.get("text", ""),
        }

    async def list_sources(self, max_points: int = 100_000) -> list[dict]:
        """Return distinct source documents with chunk counts."""
        sources: dict[str, dict] = {}
        offset = None
        total_scanned = 0

        while True:
            points, offset = self.qdrant.scroll(
                collection_name=self._collection,
                limit=100,
                with_payload=True,
                offset=offset,
            )

            for point in points:
                payload = point.payload or {}
                fp = payload.get("file_path", "unknown")
                if fp not in sources:
                    sources[fp] = {
                        "file_path": fp,
                        "file_type": payload.get("file_type", ""),
                        "chunk_count": 0,
                    }
                sources[fp]["chunk_count"] += 1

            total_scanned += len(points)
            if total_scanned >= max_points:
                logger.warning(
                    "list_sources safety cap reached: scanned %d points (cap %d). Results may be incomplete.",
                    total_scanned,
                    max_points,
                )
                break

            if offset is None or not points:
                break

        return sorted(sources.values(), key=lambda s: s["file_path"])

    async def get_stats(self) -> dict:
        """Return corpus statistics."""
        info = self.qdrant.get_collection(self._collection)
        sources = await self.list_sources()

        return {
            "total_chunks": info.points_count,
            "total_sources": len(sources),
            "embedding_model": self._embed_model,
            "collection_name": self._collection,
        }
