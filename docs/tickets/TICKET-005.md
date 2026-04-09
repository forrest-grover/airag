# TICKET-005 — Deploy TEI reranker with gte-reranker-modernbert-base

**id:** TICKET-005
**title:** Deploy TEI reranker with gte-reranker-modernbert-base
**status:** DONE
**priority:** P0
**category:** Infrastructure
**effort:** S
**depends_on:** TICKET-001

## Goal

Run TEI serving `Alibaba-NLP/gte-reranker-modernbert-base` on same GPU as embedder.

## Acceptance Criteria

- TEI reranker container running with GPU access
- Model `Alibaba-NLP/gte-reranker-modernbert-base` loaded
- Health check: `curl http://localhost:8082/health` returns 200
- Rerank test: POST to `/rerank` returns scored results
- Combined VRAM (embedder + reranker) confirmed under 4 GB

## Implementation Notes

docker-compose service:
```yaml
tei-reranker:
  image: ghcr.io/huggingface/text-embeddings-inference:120-1.9
  ports:
    - "8082:80"
  volumes:
    - ./.volumes/models:/data
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  command: --model-id Alibaba-NLP/gte-reranker-modernbert-base --port 80
```

Verify both TEI instances share GPU without conflict.

Test: `curl -s http://localhost:8082/rerank -X POST -H 'Content-Type: application/json' -d '{"query":"test","texts":["doc1","doc2"]}'`

## Completion Notes

TEI reranker running gte-reranker-modernbert-base. Graceful fallback in retriever if reranker unavailable. 2026-04-08.
