# TICKET-023 — Add JSONL file support

**id:** TICKET-023
**title:** Add JSONL file support
**status:** OPEN
**priority:** P2
**category:** Parsing/Chunking
**effort:** S
**depends_on:** TICKET-006

## Goal

Handle `.jsonl` files correctly — parse as newline-delimited JSON records instead of failing on multi-record input.

## Acceptance Criteria

- `.jsonl` extension recognized by router and dispatched to JSONL handler
- Each line parsed as independent JSON object
- Small JSONL files (≤1024 tokens total): single chunk with all records
- Large JSONL files: records grouped into chunks respecting 1024 token limit
- Malformed lines logged and skipped, not fatal
- Chunk metadata includes: line_number range per chunk, total_records count
- Unit tests: small JSONL, large JSONL, JSONL with malformed lines

## Implementation Notes

Location: `src/airag/chunking/json_chunker.py`.

Current bug: `.jsonl` classified as JSON but `json.loads()` fails on multi-record JSONL — the entire file is passed as a single string.

Fix: detect `.jsonl` extension in router → read line-by-line → `json.loads()` per line → group into token-bounded chunks.

Reuse existing JSON flattener for individual records if needed.

Also handle `.ndjson` extension as alias.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
