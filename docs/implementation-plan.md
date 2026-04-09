# airag — Implementation Plan

Generated 2026-04-08 from subagent research synthesis.

---

## A. Executive Summary

The local RAG system will expose retrieval tools to Claude Code (and any MCP-aware client) via a Python MCP server using stdio transport. The stack deviates from the original brief in three areas, all research-justified:

**Embedding model:** Qwen3-Embedding-0.6B replaces bge-large-en-v1.5. It scores 7.5 points higher on MTEB retrieval (61.83 vs 54.29), offers 32K context (vs 512 — critical for code), supports Matryoshka dimension reduction, and fits in ~1.0 GB VRAM. Fallback: nomic-embed-text-v2-moe.

**Reranker:** Alibaba-NLP/gte-reranker-modernbert-base replaces bge-reranker-v2-m3. It is explicitly TEI-supported, has 8K context (vs 512 — essential for code chunks), uses only ~0.3 GB VRAM, and runs on ModernBERT architecture. Combined VRAM with embedder: ~1.3 GB, leaving 10.7 GB headroom.

**Parsing/chunking:** tree-sitter + langchain splitters replace unstructured. The corpus is code/MD/markup/JSON — no PDFs to speak of. tree-sitter gives AST-aware code chunking at function/class boundaries. Code chunks sized at 1024 tokens (not 512) per retrieval quality research.

**Backend-profile decision: NOT building it.** Research confirms all prompt/context caching mechanics (Anthropic cache_control, OpenAI prefix caching, Gemini context caching) are client-side concerns. The retrieval layer's only obligation is returning chunks in deterministic order. One backend-agnostic configuration is optimal.

**Self-hosted LLM compatibility: comes for free.** The MCP server makes zero LLM calls and exposes a backend-agnostic tool surface. Any MCP-aware client — including those pointed at Ollama or vLLM — can consume it unmodified. One optional validation ticket included.

**Eval:** ranx for retrieval metrics (recall@k, MRR), no LLM dependency.

All components run in Docker on WSL2 Ubuntu with GPU access via the NVIDIA host driver passthrough. TEI serves both embedder and reranker. Qdrant runs CPU-only. Total Docker footprint targets under 48 GB RAM.

---

## B. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | TEI sm_120 (Blackwell) Docker image is marked "experimental" — may have stability issues | Medium | High | Fallback: use `ghcr.io/huggingface/text-embeddings-inference:1.9` (generic CUDA) or run embedder natively via sentence-transformers outside Docker. Test early (TICKET-001). |
| R2 | RTX 5070 WSL2 CUDA passthrough not verified with current driver | Medium | High | TICKET-001 explicitly verifies nvidia-smi inside WSL2 and inside a --gpus all container. If broken, escalate to NVIDIA WSL2 driver update or native Ubuntu dual-boot. |
| R3 | Qwen3-Embedding-0.6B requires transformers >= 4.51.0 — TEI image may bundle older version | Low | Medium | Verify on TICKET-004 launch. Fallback: nomic-embed-text-v2-moe (confirmed TEI-supported). |
| R4 | tree-sitter-languages wheel may not cover all target languages | Low | Low | Verify language coverage during TICKET-007. Missing languages fall back to RecursiveCharacterTextSplitter. |
| R5 | MCP server startup timeout — heavy import or model connection delays | Low | Medium | Defer all heavy initialization (Qdrant client, TEI client) to first tool call, not import time. Document in TICKET-009. |
| R6 | Docker Desktop WSL2 memory pressure with all services running | Medium | Medium | Configure .wslconfig to cap WSL2 at 48 GB (leaving 16 GB for Windows host). TICKET-001 acceptance criteria. |
| R7 | Subagent web search was blocked — CUDA/driver version numbers from training data may be stale | Medium | Low | TICKET-001 includes manual verification steps against NVIDIA docs. Flag stale info during execution. |

---

## C. Ticket List

### TICKET-001
**Title:** Verify WSL2 + Docker Desktop + NVIDIA CUDA GPU access
**Depends on:** none
**Goal:** Confirm RTX 5070 (sm_120) is accessible from WSL2 Ubuntu and from inside Docker containers with --gpus all.
**Acceptance criteria:**
- `nvidia-smi` inside WSL2 Ubuntu shows RTX 5070
- `docker run --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi` shows the GPU
- `.wslconfig` configured: memory=48GB, processors=16, swap=8GB
- Docker Desktop resource limits reviewed and aligned with .wslconfig
- Document the Windows host driver version and CUDA version reported
- Verify `/usr/lib/wsl/lib/libcuda.so` exists and is functional
**Implementation notes:**
- Check current Windows NVIDIA driver: `nvidia-smi` on Windows host
- Inside WSL2: `nvidia-smi` should work via /usr/lib/wsl passthrough
- Docker test: `docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi`
- `.wslconfig` location: `C:\Users\<username>\.wslconfig`
- After .wslconfig changes: `wsl --shutdown` then restart
**Estimated effort:** S

---

### TICKET-002
**Title:** Create project layout and Python environment
**Depends on:** TICKET-001
**Goal:** Set up the project directory structure and Python virtualenv on WSL2 ext4 filesystem.
**Acceptance criteria:**
- Project at `~/ai-workspace/airag/` with defined directory structure
- Python 3.11+ virtualenv created (via `uv` preferred)
- `pyproject.toml` with initial dependencies declared
- `.gitignore` covering venvs, __pycache__, Docker volumes, .env
- `docker-compose.yml` skeleton with service stubs for qdrant, tei-embedder, tei-reranker
- All files on ext4 (not /mnt/c)
**Implementation notes:**
```
airag/
├── docs/
│   ├── grounding/
│   └── research/
├── src/
│   └── airag/
│       ├── __init__.py
│       ├── server.py          # MCP server entry point
│       ├── retriever.py       # Qdrant search + rerank logic
│       ├── chunking/          # Parsing + chunking pipeline
│       │   ├── __init__.py
│       │   ├── router.py      # File type detection + dispatch
│       │   ├── code.py        # tree-sitter chunker
│       │   ├── markdown.py    # heading-aware MD chunker
│       │   ├── markup.py      # HTML/XML chunker
│       │   └── json_chunker.py
│       ├── ingestion.py       # Orchestrates parse → chunk → embed → upsert
│       └── models.py          # Pydantic models for chunks, metadata
├── eval/
│   ├── gold_set.json
│   └── run_eval.py
├── tests/
├── docker-compose.yml
├── pyproject.toml
├── .mcp.json
└── README.md
```
- `uv init` then `uv add mcp[cli] qdrant-client httpx`
**Estimated effort:** S

---

### TICKET-003
**Title:** Deploy Qdrant in Docker
**Depends on:** TICKET-001
**Goal:** Run Qdrant as a persistent Docker container with data stored on WSL2 ext4.
**Acceptance criteria:**
- `qdrant/qdrant` container running via docker-compose
- Data volume mounted to `~/ai-workspace/airag/.volumes/qdrant/`
- Health check passing on `http://localhost:6333/healthz`
- Collection created: `corpus` with vector size matching embedder (1024 dims), cosine distance, int8 scalar quantization enabled
- REST API accessible from WSL2
**Implementation notes:**
- docker-compose service:
  ```yaml
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./.volumes/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
  ```
- Collection creation via qdrant-client Python:
  ```python
  client.create_collection("corpus",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    quantization_config=ScalarQuantization(
      scalar=ScalarQuantizationConfig(type=ScalarType.INT8, always_ram=True)
    ))
  ```
- Qdrant is CPU-only, confirmed no GPU dependency
**Estimated effort:** S

---

### TICKET-004
**Title:** Deploy TEI embedder with Qwen3-Embedding-0.6B
**Depends on:** TICKET-001
**Goal:** Run Hugging Face TEI serving Qwen3-Embedding-0.6B on the RTX 5070 via Docker.
**Acceptance criteria:**
- TEI container running with GPU access (--gpus all)
- Model: `Qwen/Qwen3-Embedding-0.6B` loaded and responding
- Health check: `curl http://localhost:8081/health` returns 200
- Embedding test: POST to `/embed` returns 1024-dim vectors
- VRAM usage confirmed under 2 GB
**Implementation notes:**
- docker-compose service:
  ```yaml
  tei-embedder:
    image: ghcr.io/huggingface/text-embeddings-inference:120-1.9
    ports:
      - "8081:80"
    volumes:
      - ./.volumes/models:/data
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    command: --model-id Qwen/Qwen3-Embedding-0.6B --port 80
  ```
- If `120-1.9` tag fails on sm_120, try `1.9` (generic CUDA) as fallback
- If Qwen3 fails to load (transformers version issue), fall back to nomic-embed-text-v2-moe
- Test: `curl -s http://localhost:8081/embed -X POST -H 'Content-Type: application/json' -d '{"inputs":"hello world"}'`
**Estimated effort:** S

---

### TICKET-005
**Title:** Deploy TEI reranker with gte-reranker-modernbert-base
**Depends on:** TICKET-001
**Goal:** Run TEI serving the reranker model on the same GPU.
**Acceptance criteria:**
- TEI reranker container running with GPU access
- Model: `Alibaba-NLP/gte-reranker-modernbert-base` loaded
- Health check: `curl http://localhost:8082/health` returns 200
- Rerank test: POST to `/rerank` returns scored results
- Combined VRAM (embedder + reranker) confirmed under 4 GB
**Implementation notes:**
- docker-compose service:
  ```yaml
  tei-reranker:
    image: ghcr.io/huggingface/text-embeddings-inference:120-1.9
    ports:
      - "8082:80"
    volumes:
      - ./.volumes/models:/data
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    command: --model-id Alibaba-NLP/gte-reranker-modernbert-base --port 80
  ```
- Verify both TEI instances share the GPU without conflict
- Test: `curl -s http://localhost:8082/rerank -X POST -H 'Content-Type: application/json' -d '{"query":"test","texts":["doc1","doc2"]}'`
**Estimated effort:** S

---

### TICKET-006
**Title:** Build document parsing pipeline
**Depends on:** TICKET-002
**Goal:** Implement file-type-aware parsing that extracts text from code, MD, markup, and JSON files.
**Acceptance criteria:**
- File type router dispatches to correct parser based on extension
- Code parser extracts full file text with language detection
- Markdown parser preserves heading hierarchy
- HTML/XML parser extracts text content, strips tags
- JSON parser handles both small configs (whole-doc) and large structured files (key-path split)
- python-magic fallback for ambiguous extensions
- Unit tests for each parser with sample files
**Implementation notes:**
- Dependencies: `tree-sitter`, `tree-sitter-languages`, `beautifulsoup4`, `lxml`
- Router: extension map in `src/airag/chunking/router.py`
- Supported code extensions: .py, .js, .ts, .go, .rs, .java, .cpp, .c, .rb, .sh, .sql, etc.
- For code files: just read the text — tree-sitter parsing happens in the chunking step
**Estimated effort:** M

---

### TICKET-007
**Title:** Build chunking pipeline
**Depends on:** TICKET-006
**Goal:** Implement structure-aware chunking with rich metadata extraction.
**Acceptance criteria:**
- Code chunker: tree-sitter AST splits at function/class boundaries, 1024 tokens / 128 overlap
- Markdown chunker: heading-based primary split, RecursiveCharacterTextSplitter fallback for long sections, 512 tokens / 64 overlap
- HTML/XML chunker: tag-boundary splits, 512 tokens / 64 overlap
- JSON chunker: whole-document (≤1024 tokens) or key-path split for large files
- Each chunk has metadata: chunk_id, file_path, file_type, language, symbol, heading_path, json_path, token_count, chunk_index
- chunk_id = deterministic hash of file_path + byte_offset (stable across re-ingestion)
- Token counting via tiktoken (cl100k_base) or Qwen3 tokenizer
- Unit tests with sample files for each content type
**Implementation notes:**
- Code: use tree-sitter to walk CST, collect top-level function/class nodes
- Context header per code chunk: file_path + language + containing class + imports
- If function exceeds 1024 tokens, split at inner statement boundaries
- `langchain-text-splitters` for MD: `MarkdownHeaderTextSplitter` → `RecursiveCharacterTextSplitter`
- `tiktoken` for token counting
**Estimated effort:** L

---

### TICKET-008
**Title:** Build ingestion script
**Depends on:** TICKET-003, TICKET-004, TICKET-007
**Goal:** Orchestrate the full pipeline: scan directory → parse → chunk → embed → upsert to Qdrant.
**Acceptance criteria:**
- CLI command: `python -m airag.ingestion --corpus-dir /path/to/corpus`
- Scans directory recursively, respects .gitignore patterns
- Routes files through parser → chunker pipeline
- Batches chunks for embedding via TEI HTTP API
- Upserts vectors + metadata to Qdrant `corpus` collection
- Progress bar (tqdm)
- Handles incremental re-ingestion: skip unchanged files (by mtime + size hash)
- Logs stats: files processed, chunks created, time elapsed
- Tested with a small sample corpus (10-20 files)
**Implementation notes:**
- Embedding via TEI: `POST http://localhost:8081/embed` with batch of texts
- Batch size: 32-64 chunks per embedding call (tune based on VRAM)
- Qdrant upsert via qdrant-client: batch of 100 points per call
- File change detection: store file_path + mtime + size in a local SQLite or JSON sidecar
- Dependencies to add: `tqdm`, `httpx`
**Estimated effort:** M

---

### TICKET-009
**Title:** Scaffold MCP server with FastMCP
**Depends on:** TICKET-002
**Goal:** Create a minimal MCP server that Claude Code can connect to via stdio.
**Acceptance criteria:**
- `src/airag/server.py` implements FastMCP with stdio transport
- One stub tool (`ping`) returns a health check response
- No print() to stdout anywhere in server code (stderr only for logging)
- `.mcp.json` in project root with correct absolute paths
- Claude Code connects and shows the `ping` tool available
- MCP Inspector test passes: `npx @modelcontextprotocol/inspector uv --directory ~/ai-workspace/airag run src/airag/server.py`
**Implementation notes:**
- Server skeleton:
  ```python
  from mcp.server.fastmcp import FastMCP
  mcp = FastMCP("airag")

  @mcp.tool()
  async def ping() -> str:
      return "airag MCP server is running"

  if __name__ == "__main__":
      mcp.run(transport="stdio")
  ```
- `.mcp.json`:
  ```json
  {
    "mcpServers": {
      "airag": {
        "command": "uv",
        "args": ["--directory", "/home/forrest/ai-workspace/airag", "run", "src/airag/server.py"],
        "env": {
          "QDRANT_URL": "http://localhost:6333",
          "TEI_EMBED_URL": "http://localhost:8081",
          "TEI_RERANK_URL": "http://localhost:8082"
        }
      }
    }
  }
  ```
- Critical: defer all heavy initialization (Qdrant/TEI clients) to first tool call to avoid startup timeout
- All logging to stderr via stdlib `logging`
**Estimated effort:** S

---

### TICKET-010
**Title:** Implement MCP retrieval tools
**Depends on:** TICKET-008, TICKET-009
**Goal:** Implement the full tool surface: search_corpus, get_chunk, list_sources, get_corpus_stats.
**Acceptance criteria:**
- `search_corpus(query, k=5, filters=None)` — embeds query via TEI, searches Qdrant, reranks top-20→top-k via TEI reranker, returns ranked chunks with metadata
- `get_chunk(chunk_id)` — fetches single chunk from Qdrant by ID, returns full text + metadata
- `list_sources()` — returns distinct source documents with chunk counts
- `get_corpus_stats()` — returns total chunks, sources, embedding model, index info
- All tools return JSON-formatted text (not nested MCP resources) for max backend compatibility
- Chunk response format includes: chunk_id, score, source_id, file_path, file_type, section, text
- Deterministic chunk ordering for cache-friendliness
- Error handling: graceful messages if Qdrant/TEI unreachable
- MCP Inspector tests pass for all tools
**Implementation notes:**
- Retriever in `src/airag/retriever.py`:
  1. Embed query via `POST http://localhost:8081/embed`
  2. Search Qdrant with top_k=20 (over-fetch for reranking)
  3. Rerank via `POST http://localhost:8082/rerank` with query + 20 chunks
  4. Return top-k after reranking
- Use `httpx.AsyncClient` for non-blocking TEI calls
- Lazy-init clients on first tool call (not at import time)
**Estimated effort:** M

---

### TICKET-011
**Title:** Register MCP server with Claude Code and smoke test
**Depends on:** TICKET-010
**Goal:** Verify Claude Code discovers and uses the airag MCP tools end-to-end.
**Acceptance criteria:**
- Claude Code shows airag tools in `/mcp` status
- `search_corpus("test query")` returns chunks from the indexed corpus
- `get_chunk(chunk_id)` returns the expected chunk
- `list_sources()` returns the corpus manifest
- Response format renders cleanly in Claude Code's tool result display
- Claude Code can use retrieved chunks to answer a question about the corpus
**Implementation notes:**
- Start Docker services: `docker compose up -d`
- Ingest a small test corpus: `python -m airag.ingestion --corpus-dir ./tests/fixtures/sample_corpus`
- Open Claude Code in the project directory — it should auto-discover `.mcp.json`
- Test: ask Claude Code a question about the test corpus content
- If tools don't appear: check `~/.claude/config.json` for `disabledMcpjsonServers`
**Estimated effort:** S

---

### TICKET-012
**Title:** Tune tool response format for caching friendliness
**Depends on:** TICKET-010
**Goal:** Ensure chunk responses are structured to maximize client-side cache hit rates.
**Acceptance criteria:**
- Chunks returned in deterministic order (by score descending, then chunk_id for tie-breaking)
- Metadata fields ordered consistently (alphabetical or fixed schema)
- Stable JSON serialization (sorted keys, consistent formatting)
- Document the caching guidance for clients: place static context (system prompt, corpus summary) before dynamic chunks in the prompt
- Test: two identical queries return byte-identical JSON responses
**Implementation notes:**
- `json.dumps(result, sort_keys=True, ensure_ascii=False)` for deterministic serialization
- This is the RAG server's only caching responsibility — all cache_control / prefix caching is client-side
**Estimated effort:** S

---

### TICKET-013
**Title:** Build eval harness with ranx
**Depends on:** TICKET-010
**Goal:** Set up retrieval quality measurement with recall@k and MRR.
**Acceptance criteria:**
- `eval/gold_set.json` with 30-50 curated question/relevant_chunk_ids pairs
- `eval/run_eval.py` script that:
  1. Loads gold set
  2. Runs each query through the retrieval pipeline (with and without reranking)
  3. Computes recall@5, recall@10, MRR using ranx
  4. Runs `ranx.compare()` for before/after rerank comparison
  5. Prints tabular results with statistical significance
- Gold set format: `[{"query_id", "query", "relevant_chunk_ids": [...]}]`
- Can be extended for multi-configuration comparison
**Implementation notes:**
- `pip install ranx`
- Build Qrels from gold set, build Run from retrieval results
- Two runs: baseline (dense retrieval only) and reranked
- Gold set must be manually curated after initial ingestion — create a template with 5 seed questions initially, expand to 30-50 over time
**Estimated effort:** M

---

### TICKET-014 (OPTIONAL)
**Title:** Validate self-hosted LLM backend compatibility
**Depends on:** TICKET-011
**Goal:** Confirm the MCP server works unmodified with a self-hosted local model client.
**Acceptance criteria:**
- At least one MCP-aware client configured with a local model (e.g., Ollama) successfully calls airag tools
- Tool responses parse correctly
- No code changes required to the MCP server
**Implementation notes:**
- Option A: Use Claude Code pointed at a local model (if supported)
- Option B: Use another MCP client (e.g., one of the multi-LLM clients from the MCP client directory)
- Option C: Use MCP Inspector to simulate tool calls — this validates the protocol layer even without a full client
- This is a validation ticket, not an implementation ticket — zero server changes expected
- VRAM note: a local LLM competes for the same 12 GB GPU. May need to stop TEI services or use CPU inference for the LLM.
**Estimated effort:** S

---

### TICKET-015
**Title:** End-to-end smoke test with real corpus
**Depends on:** TICKET-011
**Goal:** Full pipeline validation: ingest a meaningful corpus, query via Claude Code, verify cited answers.
**Acceptance criteria:**
- Ingest at least 100 real files from the target corpus
- Ask 5 diverse questions in Claude Code that require information from the corpus
- Verify: chunks appear in Claude Code's context, answers reference correct sources
- Verify: citations are traceable back to specific files and sections
- Document any issues found and file follow-up tickets
**Implementation notes:**
- Choose a representative subset of the actual corpus (100+ files, mixed types)
- Run full ingestion pipeline
- Test queries should span: code logic questions, config lookup, markdown documentation, cross-file relationships
- Check Claude Code's tool call display to confirm chunks were retrieved
**Estimated effort:** M

---

## D. Day One Sequence

Get a minimum working pipeline with a tiny corpus before optimizing:

| Order | Ticket | What it gives you |
|---|---|---|
| 1 | **TICKET-001** | Confirmed GPU + Docker + WSL2 work together |
| 2 | **TICKET-002** | Project structure + Python env ready |
| 3 | **TICKET-003 + TICKET-004 + TICKET-009** (parallel) | Qdrant running + embedder serving + MCP server skeleton connected to Claude Code |
| 4 | **TICKET-010** (stub retriever with manual test data) | Working MCP tools, even with hardcoded test chunks |
| 5 | **TICKET-011** | Claude Code queries the RAG system end-to-end |

After Day One you have a working loop: ask a question in Claude Code → MCP server retrieves chunks → model answers with context. Everything after this (reranker, real chunking pipeline, eval harness) is optimization on a known-working base.

**Recommended Day One shortcut:** For TICKET-010, start with a simplified retriever that does dense search only (no reranker) against a handful of manually-inserted test vectors. Wire up the reranker (TICKET-005) in a follow-up pass once the basic loop works. This reduces Day One's critical path to: GPU verify → project setup → Qdrant + embedder + MCP scaffold (parallel) → tools → smoke test.
