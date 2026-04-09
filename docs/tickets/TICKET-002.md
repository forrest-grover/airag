# TICKET-002 — Create project layout and Python environment

**id:** TICKET-002
**title:** Create project layout and Python environment
**status:** DONE
**priority:** P0
**category:** Infrastructure
**effort:** S
**depends_on:** TICKET-001

## Goal

Set up project directory structure and Python virtualenv on WSL2 ext4 filesystem.

## Acceptance Criteria

- Project at `~/ai-workspace/airag/` with defined directory structure
- Python 3.11+ virtualenv created via `uv`
- `pyproject.toml` with initial dependencies declared
- `.gitignore` covering venvs, `__pycache__`, Docker volumes, `.env`
- `docker-compose.yml` skeleton with service stubs for qdrant, tei-embedder, tei-reranker
- All files on ext4 (not `/mnt/c`)

## Implementation Notes

Directory structure:
```
airag/
├── docs/
│   ├── grounding/
│   └── research/
├── src/
│   └── airag/
│       ├── __init__.py
│       ├── server.py
│       ├── retriever.py
│       ├── chunking/
│       │   ├── __init__.py
│       │   ├── router.py
│       │   ├── code.py
│       │   ├── markdown.py
│       │   ├── markup.py
│       │   └── json_chunker.py
│       ├── ingestion.py
│       └── models.py
├── eval/
│   ├── gold_set.json
│   └── run_eval.py
├── tests/
├── docker-compose.yml
├── pyproject.toml
├── .mcp.json
└── README.md
```

Init: `uv init` then `uv add mcp[cli] qdrant-client httpx`

## Completion Notes

Full project structure, `pyproject.toml`, `.gitignore`, `docker-compose.yml`, `.mcp.json` all in place. 2026-04-08.
