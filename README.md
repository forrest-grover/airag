# airag

Local RAG system exposing retrieval tools via MCP server. Targets code and documentation corpora up to ~1M chunks. The MCP server makes zero LLM calls — it handles only embedding, search, and reranking, leaving all reasoning to the connected client.

## Architecture

```
Claude Code (or any MCP client)
        │ stdio JSON-RPC
        ▼
MCP Server (src/airag/server.py)
        │ httpx
        ├──► TEI Embedder  :8081  (Docker, GPU)
        ├──► TEI Reranker  :8082  (Docker, GPU)
        └──► Qdrant        :6333  (Docker, CPU)
```

**Ingestion pipeline:** parse → chunk → embed via TEI → upsert to Qdrant

## Stack

| Component    | Choice                                                              |
|--------------|---------------------------------------------------------------------|
| Embedding    | Qwen3-Embedding-0.6B (primary), nomic-embed-text-v2-moe (fallback) |
| Reranker     | Alibaba-NLP/gte-reranker-modernbert-base                            |
| Vector DB    | Qdrant (CPU-only, Docker)                                           |
| Serving      | HuggingFace TEI with CUDA 12.8+ / sm_120 image                     |
| MCP          | Python `mcp` SDK, FastMCP decorator API, stdio transport            |
| Parsing      | tree-sitter (code), langchain splitters (markdown), beautifulsoup4 (HTML/XML) |
| Eval         | ranx (recall@k, MRR, NDCG@k)                                       |
| Package mgr  | uv + pyproject.toml                                                 |

## Prerequisites

- NVIDIA GPU with CUDA 12.8+ support (sm_120 or compatible)
- [Docker](https://docs.docker.com/engine/install/) with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Quickstart

**1. Clone and install dependencies**

```bash
git clone <repo-url> airag
cd airag
uv sync
```

**2. Start infrastructure services**

```bash
docker compose up -d
```

This starts Qdrant (`:6333`), TEI embedder (`:8081`), and TEI reranker (`:8082`). Wait for all three health checks to pass — the TEI containers download models on first start, which takes a few minutes.

```bash
docker compose ps   # verify all services are healthy
```

**3. Ingest a corpus**

```bash
uv run python -m airag.ingestion --corpus-dir /path/to/your/docs
```

**4. Register the MCP server**

Add to your `~/.claude/claude_desktop_config.json` (Claude Desktop) or `.mcp.json` (project-level):

```json
{
  "mcpServers": {
    "airag": {
      "command": "uv",
      "args": ["--directory", "/path/to/airag", "run", "src/airag/server.py"]
    }
  }
}
```

**5. Use the tools**

Once registered, the following tools are available in any MCP-compatible client:

- `search_corpus` — semantic search with reranking
- `get_chunk` — fetch a chunk by ID
- `list_sources` — enumerate indexed documents
- `get_corpus_stats` — corpus size and metadata

## MCP Tools

| Tool               | Parameters                              | Description                                      |
|--------------------|-----------------------------------------|--------------------------------------------------|
| `search_corpus`    | `query`, `k=5`, `filters=None`          | Top-k chunks with reranking. Filters accept `file_type`, `language`, or `file_path`. |
| `get_chunk`        | `chunk_id`                              | Full chunk text and metadata by ID.              |
| `list_sources`     | —                                       | All indexed sources with per-source chunk counts. |
| `get_corpus_stats` | —                                       | Total chunks, source count, embedding model info. |

All responses are deterministically ordered for client-side caching compatibility.

## Ingestion

The ingestion pipeline walks a directory, parses each file by type, chunks the content, embeds via TEI, and upserts to Qdrant.

**Supported file types:**

| Type | Parser | Chunk size |
|------|--------|------------|
| Code (Python, JS/TS, Go, Rust, Java, C/C++, Ruby, Bash) | tree-sitter | 1024 tokens / 128 overlap |
| Markdown | langchain RecursiveCharacterTextSplitter | 512 tokens / 64 overlap |
| HTML / XML | beautifulsoup4 | 512 tokens / 64 overlap |
| JSON / YAML | structured path-aware splitting | 512 tokens / 64 overlap |

A SQLite manifest (`.airag_manifest.db` inside the corpus directory) tracks content hashes for each file. Re-running ingestion skips unchanged files automatically.

Skipped automatically: `.git`, `__pycache__`, `node_modules`, `.venv`, symlinks, binary files, and files over 50 MB.

## Configuration

Environment variables override CLI defaults:

| Variable        | Default                  | Description              |
|-----------------|--------------------------|--------------------------|
| `QDRANT_URL`    | `http://localhost:6333`  | Qdrant REST endpoint     |
| `TEI_EMBED_URL` | `http://localhost:8081`  | TEI embedder endpoint    |
| `TEI_RERANK_URL`| `http://localhost:8082`  | TEI reranker endpoint    |

Ingestion CLI flags:

```
--corpus-dir PATH       Directory to ingest (required)
--qdrant-url URL        Qdrant URL (default: $QDRANT_URL or localhost:6333)
--embed-url URL         TEI embedder URL (default: $TEI_EMBED_URL or localhost:8081)
--collection NAME       Qdrant collection name (default: corpus)
--batch-size N          Embedding batch size (default: 32)
--delete-missing        Remove sources no longer present on disk from Qdrant and manifest
```

## Development

**Run tests:**

```bash
uv run pytest
```

**Debug the MCP server interactively:**

```bash
npx @modelcontextprotocol/inspector uv --directory ~/ai-workspace/airag run src/airag/server.py
```

**Run the eval harness** (requires `eval/gold_set.json`):

```bash
uv run python eval/run_eval.py
```

Eval metrics: recall@k, MRR, NDCG@k via ranx.

## Hardware

Developed and tested on:

- GPU: NVIDIA RTX 5070 (Blackwell sm_120, 12 GB GDDR7) via WSL2 CUDA passthrough
- CPU: Intel i7-12700K
- RAM: 64 GB (WSL2 capped at 48 GB)
- OS: WSL2 Ubuntu on Windows 11
