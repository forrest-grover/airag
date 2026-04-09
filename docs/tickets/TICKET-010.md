# TICKET-010 — Implement MCP retrieval tools

**id:** TICKET-010
**title:** Implement MCP retrieval tools
**status:** DONE
**priority:** P0
**category:** Retrieval
**effort:** M
**depends_on:** TICKET-008, TICKET-009

## Goal

Implement full tool surface: `search_corpus`, `get_chunk`, `list_sources`, `get_corpus_stats`.

## Acceptance Criteria

- `search_corpus(query, k=5, filters=None)` — embeds query via TEI, searches Qdrant, reranks top-20→top-k via TEI reranker, returns ranked chunks with metadata
- `get_chunk(chunk_id)` — fetches single chunk from Qdrant by ID, returns full text + metadata
- `list_sources()` — returns distinct source documents with chunk counts
- `get_corpus_stats()` — returns total chunks, sources, embedding model, index info
- All tools return JSON-formatted text (not nested MCP resources) for max client compatibility
- Chunk response includes: `chunk_id`, `score`, `source_id`, `file_path`, `file_type`, `section`, `text`
- Deterministic chunk ordering for cache-friendliness
- Error handling: graceful messages if Qdrant/TEI unreachable
- MCP Inspector tests pass for all tools

## Implementation Notes

Retriever in `src/airag/retriever.py`:
1. Embed query via `POST http://localhost:8081/embed`
2. Search Qdrant with `top_k=20` (over-fetch for reranking)
3. Rerank via `POST http://localhost:8082/rerank` with query + 20 chunks
4. Return top-k after reranking

Use `httpx.AsyncClient` for non-blocking TEI calls. Lazy-init clients on first tool call.

## Completion Notes

All 4 retrieval tools implemented with rerank fallback, deterministic ordering, JSON error handling. Security: `k` clamped [1,50], filter key allowlist, `list_sources` scroll cap (100K points). 2026-04-08.
