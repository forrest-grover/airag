# TICKET-008 — Build ingestion script

**id:** TICKET-008
**title:** Build ingestion script
**status:** DONE
**priority:** P0
**category:** Ingestion
**effort:** M
**depends_on:** TICKET-003, TICKET-004, TICKET-007

## Goal

Orchestrate full pipeline: scan directory → parse → chunk → embed → upsert to Qdrant.

## Acceptance Criteria

- CLI: `python -m airag.ingestion --corpus-dir /path/to/corpus`
- Recursive directory scan, respects `.gitignore` patterns
- Routes files through parser → chunker pipeline
- Batches chunks for embedding via TEI HTTP API
- Upserts vectors + metadata to Qdrant `corpus` collection
- Progress bar via tqdm
- Incremental re-ingestion: skips unchanged files (mtime + size hash)
- Logs stats: files processed, chunks created, time elapsed
- Tested with small sample corpus (10–20 files)

## Implementation Notes

Embedding: `POST http://localhost:8081/embed` with batch of texts. Batch size: 32–64 chunks per call (tune per VRAM).

Qdrant upsert: batch of 100 points per call via qdrant-client.

File change detection: store `file_path + mtime + size` in local SQLite or JSON sidecar.

Dependencies: `tqdm`, `httpx`

## Completion Notes

Full CLI pipeline with incremental re-ingestion. Security: symlink guard, 50 MB file size cap. Paths stored relative to `corpus_dir`. State tracking upgraded from JSON sidecar to SQLite manifest (2026-04-09). 2026-04-08.
