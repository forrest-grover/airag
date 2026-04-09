# TICKET-004 — Deploy TEI embedder with Qwen3-Embedding-0.6B

**id:** TICKET-004
**title:** Deploy TEI embedder with Qwen3-Embedding-0.6B
**status:** DONE
**priority:** P0
**category:** Infrastructure
**effort:** S
**depends_on:** TICKET-001

## Goal

Run HuggingFace TEI serving Qwen3-Embedding-0.6B on RTX 5070 via Docker.

## Acceptance Criteria

- TEI container running with GPU access (`--gpus all`)
- Model `Qwen/Qwen3-Embedding-0.6B` loaded and responding
- Health check: `curl http://localhost:8081/health` returns 200
- Embedding test: POST to `/embed` returns 1024-dim vectors
- VRAM usage confirmed under 2 GB

## Implementation Notes

docker-compose service:
```yaml
tei-embedder:
  image: ghcr.io/huggingface/text-embeddings-inference:120-1.9
  ports:
    - "8081:80"
  volumes:
    - ./.volumes/models:/data
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  command: --model-id Qwen/Qwen3-Embedding-0.6B --port 80
```

Fallbacks:
- If `120-1.9` tag fails on sm_120, try `1.9` (generic CUDA)
- If Qwen3 fails to load (transformers version), fall back to `nomic-embed-text-v2-moe`

Test: `curl -s http://localhost:8081/embed -X POST -H 'Content-Type: application/json' -d '{"inputs":"hello world"}'`

## Completion Notes

TEI embedder running Qwen3-Embedding-0.6B on sm_120 image. Healthcheck configured. 2026-04-08.
