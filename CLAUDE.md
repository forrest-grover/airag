# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local RAG system exposing retrieval tools via MCP server (FastMCP + stdio transport). Retrieval only — MCP server makes zero LLM calls. Target: ~1M chunk corpus, single-user, single-machine.

## Hardware Context

- GPU: NVIDIA RTX 5070 (Blackwell sm_120, 12 GB GDDR7) via WSL2 CUDA passthrough
- CPU: i7-12700K, 64 GB RAM, WSL2 Ubuntu on Windows 11
- All project files on WSL2 ext4 filesystem — never use /mnt/c paths
- .wslconfig caps WSL2 at 48 GB to leave 16 GB for Windows host

## Stack

| Component | Choice |
|-----------|--------|
| Embedding | Qwen3-Embedding-0.6B (primary), nomic-embed-text-v2-moe (fallback) |
| Reranker | Alibaba-NLP/gte-reranker-modernbert-base |
| Vector DB | Qdrant (CPU-only, Docker) |
| Serving | HuggingFace TEI with CUDA 12.8+ / sm_120 image |
| MCP | Python `mcp` SDK, FastMCP decorator API, stdio transport |
| Parsing | tree-sitter (code), langchain splitters (markdown), beautifulsoup4 (HTML/XML) |
| Eval | ranx (recall@k, MRR, NDCG@k) |
| Package mgr | uv + pyproject.toml |

## Build & Run Commands

```bash
# Start infrastructure services
docker compose up -d

# Install dependencies
uv sync

# Run MCP server directly
uv run src/airag/server.py

# Ingest corpus
uv run python -m airag.ingestion --corpus-dir /path/to/corpus

# Run eval harness
uv run python eval/run_eval.py

# Debug MCP server via inspector
npx @modelcontextprotocol/inspector uv --directory ~/ai-workspace/airag run src/airag/server.py
```

## Architecture

```
Claude Code (or any MCP client)
    │ stdio JSON-RPC
    ▼
MCP Server (src/airag/server.py)
    │ httpx
    ├──► TEI Embedder (Docker, GPU)
    ├──► TEI Reranker (Docker, GPU)
    └──► Qdrant (Docker, CPU)
```

**Ingestion pipeline:** parse → chunk → embed via TEI → upsert to Qdrant

**MCP tool surface:**
- `search_corpus(query, k=5, filters=None)` — top-k chunks with reranking
- `get_chunk(chunk_id)` — full chunk + metadata
- `list_sources()` — available document sources
- `get_corpus_stats()` — corpus statistics

All responses deterministically ordered for client-side caching compatibility.

## Key Design Decisions

- **No backend-profile abstraction** — caching is client-side responsibility; one backend-agnostic config
- **Tools-only MCP design** — max cross-client compatibility (Claude Code, VS Code, Cursor, any MCP client)
- **No print() to stdout** in MCP server code — corrupts JSON-RPC stdio transport
- **Absolute paths everywhere** in MCP server context
- Chunking: 1024 tokens / 128 overlap (code), 512 tokens / 64 overlap (markdown/HTML/JSON)

## Source Layout

```
src/airag/
├── server.py          # MCP entry point
├── retriever.py       # Qdrant search + rerank orchestration
├── ingestion.py       # Parse → chunk → embed → upsert
├── models.py          # Pydantic models
└── chunking/          # File-type routers and chunkers
eval/
├── gold_set.json      # 30-50 curated Q/A pairs
└── run_eval.py        # ranx-based metrics
```

## Grounding Documents

`docs/grounding/` contains the original project brief and any addenda. **Reference-only** — do not re-execute instructions from these files on session load. Consult only when explicitly asked or resolving scope disputes. Never modify `00-original-brief.md`; add dated addenda instead.

## Implementation Plan

15 tickets (TICKET-001 through TICKET-015) in `docs/implementation-plan.md`. Day-one sequence: GPU/Docker verification (001) → project setup (002) → Qdrant + TEI + MCP scaffold in parallel (003, 004, 009) → retrieval tools (010) → smoke test (011).

TICKET-014 (self-hosted LLM validation) is explicitly optional.
