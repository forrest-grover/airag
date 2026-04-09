# TICKET-013 — Build eval harness with ranx

**id:** TICKET-013
**title:** Build eval harness with ranx
**status:** DONE
**priority:** P1
**category:** Eval
**effort:** M
**depends_on:** TICKET-010

## Goal

Set up retrieval quality measurement with recall@k and MRR.

## Acceptance Criteria

- `eval/gold_set.json` with 30–50 curated question/relevant_chunk_ids pairs
- `eval/run_eval.py` script that:
  1. Loads gold set
  2. Runs each query through retrieval pipeline (with and without reranking)
  3. Computes recall@5, recall@10, MRR using ranx
  4. Runs `ranx.compare()` for before/after rerank comparison
  5. Prints tabular results with statistical significance
- Gold set format: `[{"query_id", "query", "relevant_chunk_ids": [...]}]`
- Extensible for multi-configuration comparison

## Implementation Notes

Install: `pip install ranx`. Build Qrels from gold set, build Run from retrieval results. Two runs: baseline (dense retrieval only) and reranked. Gold set must be manually curated after initial ingestion — create template with 5 seed questions initially, expand to 30–50 over time.

## Completion Notes

ranx eval harness with 30 Q/A pairs, recall@5 threshold gate, dense vs reranked comparison. Gold set is self-referential (tests airag codebase). 2026-04-08.
