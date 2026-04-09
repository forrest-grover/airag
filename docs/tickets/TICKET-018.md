# TICKET-018 — Wire up Pydantic models at runtime

**id:** TICKET-018
**title:** Wire up Pydantic models at runtime
**status:** OPEN
**priority:** P2
**category:** Quality
**effort:** S
**depends_on:** none

## Goal

Use existing Pydantic models (ChunkMetadata, ChunkResult, CorpusStats) for runtime validation instead of passing raw dicts throughout the pipeline.

## Acceptance Criteria

- `ChunkMetadata` used in ingestion pipeline for chunk metadata construction
- `ChunkResult` used in retriever for search result formatting
- `CorpusStats` used in `get_corpus_stats()` tool response
- Validation errors surface clearly, not silently swallowed
- All existing tests pass
- No performance regression on ingestion — benchmark before/after on 100-file corpus

## Implementation Notes

Locations: `src/airag/models.py` (definitions), `src/airag/retriever.py` and `src/airag/ingestion.py` (usage sites).

Current state: models defined but all data flows as raw dicts — models serve only as documentation.

Risk: Pydantic validation adds overhead per chunk — may matter at ~1M chunk scale. Benchmark.

Consider: use `.model_construct()` for hot paths (skips validation) and `.model_validate()` at ingestion/retrieval boundaries only.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
