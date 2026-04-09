# TICKET-009 — Scaffold MCP server with FastMCP

**id:** TICKET-009
**title:** Scaffold MCP server with FastMCP
**status:** DONE
**priority:** P0
**category:** MCP-Server
**effort:** S
**depends_on:** TICKET-002

## Goal

Create minimal MCP server that Claude Code can connect to via stdio.

## Acceptance Criteria

- `src/airag/server.py` implements FastMCP with stdio transport
- One stub tool (`ping`) returns health check response
- No `print()` to stdout anywhere in server code (stderr only for logging)
- `.mcp.json` in project root with correct absolute paths
- Claude Code connects and shows `ping` tool available
- MCP Inspector test passes: `npx @modelcontextprotocol/inspector uv --directory ~/ai-workspace/airag run src/airag/server.py`

## Implementation Notes

Server skeleton:

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("airag")

@mcp.tool()
async def ping() -> str:
    return "airag MCP server is running"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

`.mcp.json` config:

```json
{
  "mcpServers": {
    "airag": {
      "command": "uv",
      "args": ["--directory", "/home/forrest/ai-workspace/airag", "run", "src/airag/server.py"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "TEI_EMBED_URL": "http://localhost:8081",
        "TEI_RERANK_URL": "http://localhost:8082"
      }
    }
  }
}
```

Defer all heavy initialization (Qdrant/TEI clients) to first tool call — avoid startup timeout. All logging to stderr via stdlib `logging`.

## Completion Notes

FastMCP stdio server with ping tool, stderr-only logging, lazy Qdrant init. `.mcp.json` registered. 2026-04-08.
