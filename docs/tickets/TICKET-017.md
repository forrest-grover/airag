# TICKET-017 — Extend eval gold set beyond self-referential queries

**id:** TICKET-017
**title:** Extend eval gold set beyond self-referential queries
**status:** OPEN
**priority:** P1
**category:** Eval
**effort:** M
**depends_on:** TICKET-013

## Goal

Expand `gold_set.json` with queries against real target corpus to measure retrieval quality on production-representative data.

## Acceptance Criteria

- Gold set contains queries against at least one external corpus (not airag source)
- Minimum 20 additional Q/A pairs targeting external corpus
- Total gold set: 50+ query/relevant_chunk_ids pairs
- `eval/run_eval.py` runs successfully with expanded gold set
- Results documented: recall@5, recall@10, MRR for new queries

## Implementation Notes

Location: `eval/gold_set.json`.

Current state: 30 queries all target airag codebase — useful for regression but not representative of production workload.

Process: ingest real target corpus → manually identify ~20 queries with known relevant chunks → add to gold set.

Gold set format: `[{"query_id": "...", "query": "...", "relevant_chunk_ids": [...]}]`.

Consider separate gold set files per corpus if managing multiple corpora long-term.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
