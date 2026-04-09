# TICKET-007 — Build chunking pipeline

**id:** TICKET-007
**title:** Build chunking pipeline
**status:** DONE
**priority:** P0
**category:** Parsing/Chunking
**effort:** L
**depends_on:** TICKET-006

## Goal

Implement structure-aware chunking with rich metadata extraction for all supported file types.

## Acceptance Criteria

- Code chunker: tree-sitter AST splits at function/class boundaries, 1024 tokens / 128 overlap
- Markdown chunker: heading-based primary split, `RecursiveCharacterTextSplitter` fallback for long sections, 512 tokens / 64 overlap
- HTML/XML chunker: tag-boundary splits, 512 tokens / 64 overlap
- JSON chunker: whole-document (≤1024 tokens) or key-path split for large files
- Each chunk has metadata: `chunk_id`, `file_path`, `file_type`, `language`, `symbol`, `heading_path`, `json_path`, `token_count`, `chunk_index`
- `chunk_id` = deterministic hash of `file_path` + byte_offset (stable across re-ingestion)
- Token counting via tiktoken (`cl100k_base`) or Qwen3 tokenizer
- Unit tests with sample files for each content type

## Implementation Notes

Code chunking: walk tree-sitter CST, collect top-level function/class nodes. Context header per chunk: `file_path + language + containing class + imports`. If function exceeds 1024 tokens, split at inner statement boundaries.

Markdown: `langchain-text-splitters` — `MarkdownHeaderTextSplitter` → `RecursiveCharacterTextSplitter`

Token counting: `tiktoken`

## Completion Notes

All 4 chunkers (code, markdown, markup, JSON) implemented with correct token sizes. 10 tree-sitter grammars supported. Unit tests: 37 tests in `test_chunking.py`. Known limitation: tree-sitter walks only root-level AST nodes — class methods not individually extracted (see TICKET-022). 2026-04-08.
