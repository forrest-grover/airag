# Ticket Schema

Defines format for all airag work items. One file per ticket: `TICKET-NNN.md`.

---

## Naming

`TICKET-NNN.md` — zero-padded 3-digit ID (e.g., `TICKET-001.md`, `TICKET-023.md`).

---

## Field Definitions

| Field | Type | Values / Notes |
|---|---|---|
| `id` | string | `TICKET-NNN` — matches filename |
| `title` | string | Short descriptive title |
| `status` | enum | `DONE` \| `OPEN` \| `IN-PROGRESS` \| `OPTIONAL` \| `BLOCKED` |
| `priority` | enum | `P0` (must fix) \| `P1` (should fix) \| `P2` (nice to have) |
| `category` | enum | See category table below |
| `effort` | enum | `S` (hours) \| `M` (half-day to day) \| `L` (multi-day) |
| `depends_on` | list / string | `TICKET-NNN` IDs or `none` |
| `goal` | string | 1–2 sentence objective — what and why |
| `acceptance_criteria` | list | Verifiable, binary conditions; each passes or fails |
| `implementation_notes` | text | Technical details, code snippets, doc refs |
| `completion_notes` | text | Filled when DONE — what was delivered, gaps, date |

---

## Categories

| Category | Scope |
|---|---|
| `Infrastructure` | Docker, GPU, WSL2, environment setup |
| `Parsing/Chunking` | File parsing, chunking pipeline, splitters |
| `Ingestion` | Orchestration script, embed + upsert pipeline |
| `MCP-Server` | FastMCP scaffold, server lifecycle, tool registration |
| `Retrieval` | Qdrant search, reranking, response formatting |
| `Eval` | Gold set, eval harness, metrics |
| `Quality` | Schema correctness, data integrity, code hygiene |

---

## File Template

```markdown
# TICKET-NNN — <Title>

**id:** TICKET-NNN
**title:** <Short descriptive title>
**status:** OPEN
**priority:** P0 | P1 | P2
**category:** Infrastructure | Parsing/Chunking | Ingestion | MCP-Server | Retrieval | Eval | Quality
**effort:** S | M | L
**depends_on:** TICKET-NNN, TICKET-NNN | none

## Goal

<1–2 sentence objective.>

## Acceptance Criteria

- <Verifiable condition>
- <Verifiable condition>

## Implementation Notes

<Technical details, references, code snippets.>

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
```
