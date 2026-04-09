# TICKET-011 — Register MCP server with Claude Code and smoke test

**id:** TICKET-011
**title:** Register MCP server with Claude Code and smoke test
**status:** DONE
**priority:** P0
**category:** MCP-Server
**effort:** S
**depends_on:** TICKET-010

## Goal

Verify Claude Code discovers and uses airag MCP tools end-to-end.

## Acceptance Criteria

- Claude Code shows airag tools in `/mcp` status
- `search_corpus("test query")` returns chunks from indexed corpus
- `get_chunk(chunk_id)` returns expected chunk
- `list_sources()` returns corpus manifest
- Response format renders cleanly in Claude Code's tool result display
- Claude Code can use retrieved chunks to answer question about corpus

## Implementation Notes

1. Start Docker services: `docker compose up -d`
2. Ingest small test corpus: `python -m airag.ingestion --corpus-dir ./tests/fixtures/sample_corpus`
3. Open Claude Code in project directory — auto-discovers `.mcp.json`
4. Test: ask Claude Code a question about test corpus content
5. If tools don't appear: check `~/.claude/config.json` for `disabledMcpjsonServers`

## Completion Notes

Smoke test script (`tests/smoke_test.py`) validates all 4 tools against live services. Fixture corpus (5 files) ingested and verified. MCP server responds to JSON-RPC init handshake. 2026-04-08.
