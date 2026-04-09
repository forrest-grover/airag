# TICKET-014 — Validate self-hosted LLM backend compatibility

**id:** TICKET-014
**title:** Validate self-hosted LLM backend compatibility
**status:** OPTIONAL
**priority:** P2
**category:** MCP-Server
**effort:** S
**depends_on:** TICKET-011

## Goal

Confirm MCP server works unmodified with self-hosted local model client.

## Acceptance Criteria

- At least one MCP-aware client configured with local model (e.g., Ollama) successfully calls airag tools
- Tool responses parse correctly
- No code changes required to MCP server

## Implementation Notes

Option A: Use Claude Code pointed at local model (if supported).
Option B: Use another MCP client (e.g., multi-LLM client from MCP client directory).
Option C: Use MCP Inspector to simulate tool calls — validates protocol layer without full client.

Validation ticket, not implementation — zero server changes expected. VRAM note: local LLM competes for same 12 GB GPU; may need to stop TEI services or use CPU inference.

## Completion Notes

Not attempted per plan. MCP server is backend-agnostic by design.
