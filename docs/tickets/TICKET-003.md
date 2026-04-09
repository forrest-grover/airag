# TICKET-003 — Deploy Qdrant in Docker

**id:** TICKET-003
**title:** Deploy Qdrant in Docker
**status:** DONE
**priority:** P0
**category:** Infrastructure
**effort:** S
**depends_on:** TICKET-001

## Goal

Run Qdrant as persistent Docker container with data stored on WSL2 ext4.

## Acceptance Criteria

- `qdrant/qdrant` container running via docker-compose
- Data volume mounted to `~/ai-workspace/airag/.volumes/qdrant/`
- Health check passing on `http://localhost:6333/healthz`
- Collection created: `corpus` with 1024-dim vectors, cosine distance, int8 scalar quantization
- REST API accessible from WSL2

## Implementation Notes

docker-compose service:
```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
    - "6334:6334"
  volumes:
    - ./.volumes/qdrant:/qdrant/storage
  environment:
    - QDRANT__SERVICE__GRPC_PORT=6334
```

Collection creation via qdrant-client:
```python
client.create_collection("corpus",
  vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
  quantization_config=ScalarQuantization(
    scalar=ScalarQuantizationConfig(type=ScalarType.INT8, always_ram=True)
  ))
```

Qdrant CPU-only — no GPU dependency.

## Completion Notes

Qdrant container running with healthcheck, localhost-only binding. Collection created manually or on first upsert. 2026-04-08.
