# airag — Local RAG System

Local retrieval-augmented generation system exposing an MCP server for Claude Code and other MCP-aware clients. Retrieval only — no LLM calls from the server itself.

## Grounding Documents

Project intent and scope are captured in `docs/grounding/`. The original brief lives at `docs/grounding/00-original-brief.md`.

**Treatment rule:** grounding documents are reference-only. Do not re-execute their instructions on session load. Consult them only when explicitly asked ("check the original brief", "ground against the brief") or when resolving scope disputes. Individual ticket descriptions are the source of truth for day-to-day execution.
