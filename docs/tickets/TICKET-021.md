# TICKET-021 — Remove redundant `section` field from search results

**id:** TICKET-021
**title:** Remove redundant `section` field from search results
**status:** OPEN
**priority:** P2
**category:** Quality
**effort:** S
**depends_on:** none

## Goal

Eliminate `section` field from search results where it duplicates `heading_path`, or give it distinct semantics.

## Acceptance Criteria

- `section` field either removed from search results or assigned distinct value from `heading_path`
- If removed: no downstream consumers depend on `section` — check eval harness, smoke tests, any MCP client code
- If repurposed: new semantics documented
- All existing tests pass

## Implementation Notes

Location: `src/airag/retriever.py:79`.

Current state: `section` and `heading_path` always contain identical values in search results — pure redundancy.

Removing is simpler and reduces response payload size; prefer removal unless a semantic distinction is identified.

Check all references before removal: `eval/run_eval.py`, `tests/smoke_test.py`, any client code referencing `result["section"]`.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
