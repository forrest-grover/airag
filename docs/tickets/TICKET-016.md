# TICKET-016 — Fix sub-chunk byte offset approximation

**id:** TICKET-016
**title:** Fix sub-chunk byte offset approximation
**status:** OPEN
**priority:** P1
**category:** Parsing/Chunking
**effort:** S
**depends_on:** none

## Goal

Replace approximate byte offsets in sub-chunk splits with cumulative byte offsets for stable, deterministic chunk_ids.

## Acceptance Criteria

- Sub-segments in `code.py` use cumulative byte offsets instead of token-ratio approximations
- chunk_ids remain stable across re-ingestion of unchanged files
- Existing tests in `test_chunking.py` still pass
- New test: verify chunk_id stability for file that produces sub-chunks

## Implementation Notes

Location: `src/airag/chunking/code.py:163`.

Current behavior: when function/class exceeds 1024 tokens and gets split into sub-segments, byte offsets approximated from token ratios.

Fix: track cumulative byte length as sub-segments are created.

chunk_id = hash(file_path + byte_offset) — offset accuracy directly affects ID stability.

Risk: changing offsets will invalidate chunk_ids for already-ingested files → requires re-ingestion of affected corpus.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
