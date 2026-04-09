# Ticket Index

Tracks all airag work items: infrastructure through eval. Field definitions: [SCHEMA.md](SCHEMA.md).

23 tickets: 14 done, 8 open, 0 in-progress, 1 optional

---

## Open

| ID | Title | Priority | Category | Effort | Depends On |
|---|---|---|---|---|---|
| TICKET-016 | Fix sub-chunk byte offset approximation | P1 | Parsing/Chunking | S | none |
| TICKET-017 | Extend eval gold set beyond self-referential queries | P1 | Eval | M | TICKET-013 |
| TICKET-018 | Wire up Pydantic models at runtime | P2 | Quality | S | none |
| TICKET-019 | Add python-magic MIME-type fallback for unknown extensions | P2 | Parsing/Chunking | S | none |
| TICKET-020 | Address float score nondeterminism in reranker | P2 | Retrieval | S | none |
| TICKET-021 | Remove redundant `section` field from search results | P2 | Quality | S | none |
| TICKET-022 | Extract nested definitions in tree-sitter chunker | P2 | Parsing/Chunking | M | TICKET-007 |
| TICKET-023 | Add JSONL file support | P2 | Parsing/Chunking | S | TICKET-006 |

---

## Done

| ID | Title | Priority | Category | Effort | Depends On |
|---|---|---|---|---|---|
| TICKET-001 | Verify WSL2 + Docker + NVIDIA CUDA GPU access | P0 | Infrastructure | S | none |
| TICKET-002 | Create project layout and Python environment | P0 | Infrastructure | S | TICKET-001 |
| TICKET-003 | Deploy Qdrant in Docker | P0 | Infrastructure | S | TICKET-001 |
| TICKET-004 | Deploy TEI embedder with Qwen3-Embedding-0.6B | P0 | Infrastructure | S | TICKET-001 |
| TICKET-005 | Deploy TEI reranker with gte-reranker-modernbert-base | P0 | Infrastructure | S | TICKET-001 |
| TICKET-006 | Build document parsing pipeline | P0 | Parsing/Chunking | M | TICKET-002 |
| TICKET-007 | Build chunking pipeline | P0 | Parsing/Chunking | L | TICKET-006 |
| TICKET-008 | Build ingestion script | P0 | Ingestion | M | TICKET-003, TICKET-004, TICKET-007 |
| TICKET-009 | Scaffold MCP server with FastMCP | P0 | MCP-Server | S | TICKET-002 |
| TICKET-010 | Implement MCP retrieval tools | P0 | Retrieval | M | TICKET-008, TICKET-009 |
| TICKET-011 | Register MCP server with Claude Code and smoke test | P0 | MCP-Server | S | TICKET-010 |
| TICKET-012 | Tune tool response format for caching friendliness | P1 | Retrieval | S | TICKET-010 |
| TICKET-013 | Build eval harness with ranx | P1 | Eval | M | TICKET-010 |
| TICKET-015 | End-to-end smoke test with real corpus | P0 | Eval | M | TICKET-008, TICKET-011 |

---

## Optional

| ID | Title | Priority | Category | Effort | Depends On |
|---|---|---|---|---|---|
| TICKET-014 | Validate self-hosted LLM backend compatibility | P2 | MCP-Server | S | TICKET-011 |
