# TICKET-020 — Address float score nondeterminism in reranker

**id:** TICKET-020
**title:** Address float score nondeterminism in reranker
**status:** OPEN
**priority:** P2
**category:** Retrieval
**effort:** S
**depends_on:** none

## Goal

Investigate and mitigate float score variation across identical reranker inference runs to preserve response determinism established in TICKET-012.

## Acceptance Criteria

- Document whether TEI reranker produces identical scores for identical inputs across runs
- If nondeterministic: quantify variation (e.g., ±0.001)
- If variation affects sort order: implement rounding or epsilon-based tie-breaking
- If variation is cosmetic only: document as known behavior, no code change needed
- Test: run same query 10 times, compare JSON output for byte-equality

## Implementation Notes

Location: `src/airag/retriever.py`.

Context: TICKET-012 achieved deterministic JSON serialization. Float scores from GPU inference may vary between runs due to CUDA non-determinism.

Options:
1. Round scores to N decimal places before serialization
2. Accept cosmetic variation — only relevant if it changes sort order
3. `torch.use_deterministic_algorithms(True)` if TEI exposes a flag for it

Sort is `(-score, chunk_id)` — small float variations could theoretically swap adjacent results with near-identical scores, changing retrieved context.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
