"""MCP server entry point for airag."""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from airag.retriever import Retriever

# All logging to stderr — stdout is reserved for JSON-RPC
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("airag")

mcp = FastMCP("airag")
retriever = Retriever()


@mcp.tool()
async def ping() -> str:
    """Health check — returns a confirmation that the airag MCP server is running."""
    return "airag MCP server is running"


@mcp.tool()
async def search_corpus(
    query: str, k: int = 5, filters: str | dict | None = None
) -> str:
    """Search the corpus for chunks relevant to a query.

    Args:
        query: The search query text.
        k: Number of top results to return (default 5).
        filters: Optional metadata filters — accepts a dict or a JSON string,
                 e.g. {"file_type": "python"} or '{"file_type": "python"}'.

    Returns:
        JSON string with ranked chunk results.
    """
    ALLOWED_FILTER_KEYS = {"file_type", "language", "file_path"}

    try:
        k = max(1, min(k, 50))

        if isinstance(filters, dict):
            filter_dict = filters
        elif isinstance(filters, str):
            filter_dict = json.loads(filters)
        else:
            filter_dict = None

        if filter_dict is not None:
            unknown = set(filter_dict.keys()) - ALLOWED_FILTER_KEYS
            if unknown:
                return json.dumps(
                    {
                        "error": f"Unknown filter keys: {sorted(unknown)}. Allowed: {sorted(ALLOWED_FILTER_KEYS)}"
                    }
                )

        results = await retriever.search(query, k=k, filters=filter_dict)
        return json.dumps(results, sort_keys=True, ensure_ascii=False)
    except Exception as e:
        logger.error("search_corpus error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_chunk(chunk_id: str) -> str:
    """Fetch a single chunk by its ID.

    Args:
        chunk_id: The unique identifier of the chunk.

    Returns:
        JSON string with the chunk data, or an error if not found.
    """
    try:
        result = await retriever.get_chunk(chunk_id)
        if result is None:
            return json.dumps({"error": f"Chunk '{chunk_id}' not found"})
        return json.dumps(result, sort_keys=True, ensure_ascii=False)
    except Exception as e:
        logger.error("get_chunk error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_sources() -> str:
    """List all document sources in the corpus with chunk counts.

    Returns:
        JSON string with a list of sources.
    """
    try:
        sources = await retriever.list_sources()
        return json.dumps(sources, sort_keys=True, ensure_ascii=False)
    except Exception as e:
        logger.error("list_sources error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_corpus_stats() -> str:
    """Get corpus statistics including total chunks, sources, and embedding model info.

    Returns:
        JSON string with corpus statistics.
    """
    try:
        stats = await retriever.get_stats()
        return json.dumps(stats, sort_keys=True, ensure_ascii=False)
    except Exception as e:
        logger.error("get_corpus_stats error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


def main():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
