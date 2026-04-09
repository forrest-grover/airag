# Subagent Research Summaries

Captured 2026-04-08. Reference material for ticket implementation.

## 1. Blackwell + WSL2 Compatibility (PARTIAL — web blocked)
- PyTorch 2.11.0 stable has CUDA 12.8 wheels: `pip install torch --index-url https://download.pytorch.org/whl/cu128`
- CUDA 13.0 wheels also available (cu130)
- sm_120 support in stable builds not explicitly confirmed — needs manual verification
- Verification URLs provided for manual check (NVIDIA WSL docs, CUDA toolkit release notes, TEI releases)

## 2. Embedding Model Selection
- **Primary: Qwen3-Embedding-0.6B** — MTEB retrieval 61.83, 1024 dims (MRL 32-1024), 32K context, ~1.0GB FP16, Apache 2.0
- **Fallback: nomic-embed-text-v2-moe** — 475M params (305M active), 768 dims, 512 context, ~0.6GB, Apache 2.0
- bge-large-en-v1.5 superseded (54.29 MTEB, 512 context limit)
- TEI Blackwell image: `ghcr.io/huggingface/text-embeddings-inference:120-1.9` (experimental)
- Qwen3 requires transformers >= 4.51.0

## 3. Reranker Selection
- **Primary: Alibaba-NLP/gte-reranker-modernbert-base** — 149M params, ~0.3GB FP16, 8K context, BEIR 56.73, Apache 2.0, explicitly TEI-listed
- bge-reranker-v2-m3: 512 token limit (bad for code), not explicitly in TEI supported list
- Qwen3-Reranker: best code scores but NOT TEI-compatible (CausalLM arch, needs vLLM)
- Jina reranker: CC-BY-NC-4.0, JinaBERT not in TEI reranker list
- Combined VRAM (Qwen3-Embed + gte-reranker): ~1.3GB, leaving 10.7GB headroom

## 4. Claude Code MCP Integration
- **MCP confirmed as the right pattern** — production-stable, protocol version 2025-11-25
- **Python SDK:** `mcp` on PyPI (Tier 1), `FastMCP` decorator API
- **Transport: stdio** — both Claude Code and server inside WSL2, simplest path
- **Registration:** `.mcp.json` in project root or `~/.claude/config.json` mcpServers key
- **Tools-only design** for max cross-client compatibility
- **Critical:** no print() to stdout (corrupts JSON-RPC), absolute paths everywhere, explicit env vars
- **Debugging:** MCP Inspector (`npx @modelcontextprotocol/inspector`)
- Cross-client compatible (VS Code, Cursor, multi-LLM clients confirmed)

## 5. Caching & Backend Optimization (PARTIAL — web blocked)
- **Decision: NO backend-profile abstraction**
- Rationale: CLIENT assembles prompt and calls LLM; all caching mechanics are client-side
- Retrieval layer's only caching-relevant job: return chunks in deterministic, stable order
- Anthropic: explicit cache_control breakpoints, client-side
- OpenAI: automatic prefix caching, client-side
- Gemini: explicit caching API with separate pre-call, client-side
- No retrieval-layer differences between Haiku/Sonnet/Opus

## 6. Chunking & Parsing
- **Skip unstructured/docling/marker** — PDF-focused, overkill
- Code: tree-sitter + tree-sitter-languages (AST-aware, 1024 tok / 128 overlap)
- Markdown: langchain MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter (512 tok / 64 overlap)
- HTML/XML: beautifulsoup4 + lxml (512 tok / 64 overlap)
- JSON: stdlib json + key-path walker (whole doc up to 1024 tok, 0 overlap)
- Rich metadata: chunk_id, file_path, file_type, language, symbol, heading_path, json_path, token_count
- Deps: tree-sitter, tree-sitter-languages, langchain-text-splitters, beautifulsoup4, lxml, tiktoken

## 7. Eval Harness
- **Recommendation: ranx** — `pip install ranx`
- Native recall@k, MRR, NDCG@k
- Built-in `compare()` for multi-run statistical comparison
- No LLM calls required
- RAGAS/TruLens rejected (require LLM calls for most metrics)
- Gold set: 30-50 query/relevant_chunk_ids pairs in JSON
