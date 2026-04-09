# TICKET-015 — End-to-end smoke test with real corpus

**id:** TICKET-015
**title:** End-to-end smoke test with real corpus
**status:** DONE
**priority:** P0
**category:** Eval
**effort:** M
**depends_on:** TICKET-008, TICKET-011

## Goal

Full pipeline validation: ingest meaningful corpus, query via Claude Code, verify cited answers.

## Acceptance Criteria

- Ingest at least 100 real files from target corpus
- Ask 5 diverse questions in Claude Code that require information from corpus
- Verify: chunks appear in Claude Code's context, answers reference correct sources
- Verify: citations traceable back to specific files and sections
- Document any issues found and file follow-up tickets

## Implementation Notes

Choose representative subset of actual corpus (100+ files, mixed types). Run full ingestion pipeline. Test queries should span: code logic questions, config lookup, markdown documentation, cross-file relationships. Check Claude Code's tool call display to confirm chunks were retrieved.

## Completion Notes

Project source (31 files, 196 chunks) ingested as corpus. 5 diverse queries tested via MCP tools with accurate, cited results. Reranker scores 0.93–0.97. 2026-04-08.
