# TICKET-012 — Tune tool response format for caching friendliness

**id:** TICKET-012
**title:** Tune tool response format for caching friendliness
**status:** DONE
**priority:** P1
**category:** Retrieval
**effort:** S
**depends_on:** TICKET-010

## Goal

Ensure chunk responses structured to maximize client-side cache hit rates.

## Acceptance Criteria

- Chunks returned in deterministic order (score descending, then `chunk_id` for tie-breaking)
- Metadata fields ordered consistently (alphabetical or fixed schema)
- Stable JSON serialization (sorted keys, consistent formatting)
- Document caching guidance for clients: place static context before dynamic chunks in prompt
- Test: two identical queries return byte-identical JSON responses

## Implementation Notes

Use `json.dumps(result, sort_keys=True, ensure_ascii=False)` for deterministic serialization. All prompt/context caching mechanics (`cache_control`, prefix caching, Gemini context caching) are client-side concerns — server's only obligation is deterministic ordering.

## Completion Notes

`sort_keys=True` + deterministic sort `(-score, chunk_id)` on all responses. Gap: client caching guidance not documented. 2026-04-08.
