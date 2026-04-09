"""TICKET-011: End-to-end smoke test for MCP retrieval tools."""

import asyncio
import sys

from airag.retriever import Retriever


async def main() -> int:
    retriever = Retriever()
    passed = 0
    failed = 0

    # Test 1: search_corpus
    print("=" * 60)
    print("TEST 1: search_corpus")
    try:
        results = await retriever.search("fibonacci sequence generator", k=3)
        assert len(results) > 0, "No search results returned"
        assert any(
            "calculator" in r.get("file_path", "") for r in results
        ), "Expected calculator.py in results"
        print(f"  PASS — {len(results)} results, top: {results[0]['file_path']}")
        print(
            f"         score={results[0]['score']:.4f}, chunk_id={results[0]['chunk_id']}"
        )
        passed += 1
    except Exception as e:
        print(f"  FAIL — {e}")
        failed += 1

    # Test 2: get_chunk
    print("TEST 2: get_chunk")
    try:
        if results:
            chunk_id = results[0]["chunk_id"]
            chunk = await retriever.get_chunk(chunk_id)
            assert chunk is not None, f"Chunk {chunk_id} not found"
            assert chunk["text"], "Chunk text is empty"
            print(f"  PASS — retrieved chunk {chunk_id}, {len(chunk['text'])} chars")
        else:
            print("  SKIP — no results from search")
    except Exception as e:
        print(f"  FAIL — {e}")
        failed += 1
    else:
        passed += 1

    # Test 3: list_sources
    print("TEST 3: list_sources")
    try:
        sources = await retriever.list_sources()
        assert len(sources) > 0, "No sources returned"
        fixture_sources = [s for s in sources if "sample_corpus" in s["file_path"]]
        assert (
            len(fixture_sources) >= 5
        ), f"Expected >=5 fixture sources, got {len(fixture_sources)}"
        print(
            f"  PASS — {len(sources)} total sources, {len(fixture_sources)} from fixtures"
        )
        for s in fixture_sources:
            print(f"         {s['file_path']} ({s['chunk_count']} chunks)")
        passed += 1
    except Exception as e:
        print(f"  FAIL — {e}")
        failed += 1

    # Test 4: get_corpus_stats
    print("TEST 4: get_corpus_stats")
    try:
        stats = await retriever.get_stats()
        assert stats["total_chunks"] > 0, "No chunks in corpus"
        assert stats["total_sources"] > 0, "No sources in corpus"
        print(
            f"  PASS — {stats['total_chunks']} chunks, {stats['total_sources']} sources"
        )
        passed += 1
    except Exception as e:
        print(f"  FAIL — {e}")
        failed += 1

    # Summary
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
