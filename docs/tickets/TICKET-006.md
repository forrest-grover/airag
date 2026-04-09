# TICKET-006 — Build document parsing pipeline

**id:** TICKET-006
**title:** Build document parsing pipeline
**status:** DONE
**priority:** P0
**category:** Parsing/Chunking
**effort:** M
**depends_on:** TICKET-002

## Goal

Implement file-type-aware parsing that extracts text from code, Markdown, markup, and JSON files.

## Acceptance Criteria

- File type router dispatches to correct parser based on extension
- Code parser extracts full file text with language detection
- Markdown parser preserves heading hierarchy
- HTML/XML parser extracts text content, strips tags
- JSON parser handles small configs (whole-doc) and large structured files (key-path split)
- python-magic fallback for ambiguous extensions
- Unit tests for each parser with sample files

## Implementation Notes

Dependencies: `tree-sitter`, `tree-sitter-languages`, `beautifulsoup4`, `lxml`

Router: extension map in `src/airag/chunking/router.py`

Supported code extensions: `.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.cpp`, `.c`, `.rb`, `.sh`, `.sql`, etc.

For code files: read text only — tree-sitter parsing happens in chunking step.

## Completion Notes

File type router with extension/filename maps, all parsers implemented. python-magic fallback NOT implemented (deferred — low priority for code/MD corpus). Unit tests: 22 tests in `test_parsing.py`. 2026-04-08.
