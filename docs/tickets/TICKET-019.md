# TICKET-019 — Add python-magic MIME-type fallback for unknown extensions

**id:** TICKET-019
**title:** Add python-magic MIME-type fallback for unknown extensions
**status:** OPEN
**priority:** P2
**category:** Parsing/Chunking
**effort:** S
**depends_on:** none

## Goal

Use MIME-type detection via python-magic for files with unknown or missing extensions, rather than defaulting silently to plain text.

## Acceptance Criteria

- `python-magic` added to project dependencies
- Router falls back to MIME-type detection when extension not in known map
- Text MIME types routed to appropriate parser: `text/x-python` → code, `text/html` → markup, etc.
- Binary files detected and skipped with warning log
- Unit tests: extensionless Python file, extensionless HTML file, binary file

## Implementation Notes

Location: `src/airag/chunking/router.py`.

Current behavior: unknown extensions default to plain text parser.

`python-magic` uses libmagic — may need `apt install libmagic1` in some environments. Document in README if added.

Alternative: `filetype` package (pure Python, no system dep) — less accurate but simpler deployment.

MIME-to-parser map: `text/x-python` → code, `text/html` → markup, `application/json` → JSON, `text/x-c` / `text/x-java-source` → code, etc.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
