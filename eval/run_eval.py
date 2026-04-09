"""Eval harness: compare dense-only vs reranked retrieval using ranx metrics."""

import asyncio
import json
import sys
from pathlib import Path

from ranx import Qrels, Run, compare

from airag.retriever import Retriever

METRICS = ["recall@5", "recall@10", "mrr", "ndcg@5", "ndcg@10"]
RECALL5_THRESHOLD = 0.3


def log(msg: str) -> None:
    """Print to stderr to avoid corrupting stdout."""
    print(msg, file=sys.stderr)


async def run_dense(retriever: Retriever, query: str, k: int = 10) -> list[dict]:
    """Embed query, search Qdrant top-20, return top-k WITHOUT reranking."""
    query_vector = await retriever.embed(query)

    results = retriever.qdrant.query_points(
        collection_name=retriever._collection,
        query=query_vector,
        limit=20,
        with_payload=True,
    )

    chunks = []
    for point in results.points:
        payload = point.payload or {}
        chunks.append({
            "chunk_id": payload.get("chunk_id", str(point.id)),
            "score": point.score,
        })

    chunks.sort(key=lambda c: (-c["score"], c["chunk_id"]))
    return chunks[:k]


async def run_reranked(retriever: Retriever, query: str, k: int = 10) -> list[dict]:
    """Embed query, search Qdrant top-20, rerank via TEI, return top-k."""
    results = await retriever.search(query, k=k)
    return [{"chunk_id": c["chunk_id"], "score": c["score"]} for c in results]


async def main() -> None:
    gold_path = Path(__file__).parent / "gold_set.json"
    if not gold_path.exists():
        log(f"ERROR: gold set not found at {gold_path}")
        sys.exit(1)

    gold_set = json.loads(gold_path.read_text())
    if not gold_set:
        log("ERROR: gold_set.json is empty — add query/relevant_chunk_ids pairs first")
        sys.exit(1)

    # Build qrels from gold set
    qrels_dict = {
        item["query_id"]: {cid: 1 for cid in item["relevant_chunk_ids"]}
        for item in gold_set
    }
    qrels = Qrels(qrels_dict)

    retriever = Retriever()

    # Run both configurations for every query
    dense_run_dict: dict[str, dict[str, float]] = {}
    reranked_run_dict: dict[str, dict[str, float]] = {}

    for item in gold_set:
        qid = item["query_id"]
        query = item["query"]
        log(f"  Evaluating {qid}: {query[:60]}...")

        dense_results = await run_dense(retriever, query, k=10)
        reranked_results = await run_reranked(retriever, query, k=10)

        dense_run_dict[qid] = {c["chunk_id"]: c["score"] for c in dense_results}
        reranked_run_dict[qid] = {c["chunk_id"]: c["score"] for c in reranked_results}

    dense_run = Run(dense_run_dict, name="dense_only")
    reranked_run = Run(reranked_run_dict, name="reranked")

    # Compare both runs side by side
    log("\n" + "=" * 60)
    log("EVAL RESULTS")
    log("=" * 60)

    report = compare(
        qrels=qrels,
        runs=[dense_run, reranked_run],
        metrics=METRICS,
    )
    log(str(report))

    # Check threshold gate
    report_dict = report.to_dict()
    dense_recall5 = float(report_dict["dense_only"]["scores"]["recall@5"])
    reranked_recall5 = float(report_dict["reranked"]["scores"]["recall@5"])
    best_recall5 = max(dense_recall5, reranked_recall5)

    if best_recall5 < RECALL5_THRESHOLD:
        log(
            f"\nFAIL: best recall@5 = {best_recall5:.3f} < threshold {RECALL5_THRESHOLD}"
        )
        sys.exit(1)

    log(f"\nPASS: best recall@5 = {best_recall5:.3f} >= threshold {RECALL5_THRESHOLD}")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
