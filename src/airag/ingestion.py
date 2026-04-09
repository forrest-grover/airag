"""Parse, chunk, embed, and upsert pipeline."""

import argparse
import fnmatch
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams
from tqdm import tqdm

from airag.chunking import chunk_file
from airag.manifest import delete_source, get_source, list_stale_paths, open_manifest, upsert_source

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("airag")

VECTOR_DIMENSION = 1024

# Default gitignore-like patterns to skip
SKIP_PATTERNS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".volumes",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    "*.egg-info",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

SKIP_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".lock",
    ".sum",
    ".bin",
    ".dat",
    ".db",
    ".sqlite",
}


def should_skip(path: Path) -> bool:
    """Check if a file/dir should be skipped."""
    # Skip hidden files/dirs (except specific ones)
    if path.name.startswith(".") and path.name not in (
        ".gitignore",
        ".dockerignore",
        ".editorconfig",
        ".env",
    ):
        return True
    # Skip known dirs
    if path.is_dir() and any(fnmatch.fnmatch(path.name, p) for p in SKIP_PATTERNS):
        return True
    # Skip binary/non-text extensions
    if path.is_file() and path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    return False


def scan_directory(corpus_dir: Path) -> list[Path]:
    """Recursively scan directory for indexable files."""
    files = []
    for item in sorted(corpus_dir.rglob("*")):
        # Check if any parent should be skipped
        skip = False
        for parent in item.relative_to(corpus_dir).parents:
            if parent.name and should_skip(corpus_dir / parent):
                skip = True
                break
        if skip:
            continue
        if item.is_symlink():
            logger.warning("Skipping symlink: %s", item)
            continue
        if item.is_file() and not should_skip(item):
            # Skip empty files
            size = item.stat().st_size
            if size > MAX_FILE_SIZE:
                logger.warning("Skipping oversized file: %s (%d bytes)", item, size)
                continue
            if size > 0:
                files.append(item)
    return files


def embed_batch(texts: list[str], embed_url: str, client: httpx.Client) -> list[list[float]]:
    """Embed a batch of texts via TEI synchronously."""
    resp = client.post(
        f"{embed_url}/embed",
        json={"inputs": texts},
    )
    resp.raise_for_status()
    return resp.json()


def load_state(state_path: Path) -> dict:
    """Load ingestion state (file hashes for incremental re-ingestion)."""
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {}


def save_state(state_path: Path, state: dict):
    """Save ingestion state."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2))


def file_hash(path: Path) -> str:
    """Hash file by mtime + size for change detection."""
    stat = path.stat()
    key = f"{path}:{stat.st_mtime}:{stat.st_size}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def ensure_collection(client: QdrantClient, collection: str) -> None:
    """Create the Qdrant collection if it doesn't already exist."""
    existing = [c.name for c in client.get_collections().collections]
    if collection in existing:
        logger.info("Collection '%s' already exists", collection)
        # Ensure indexes exist even on pre-existing collections
        ensure_payload_indexes(client, collection)
        return

    logger.info(
        "Creating collection '%s' (dim=%d, cosine)", collection, VECTOR_DIMENSION
    )
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(
            size=VECTOR_DIMENSION,
            distance=Distance.COSINE,
        ),
    )

    # Create payload indexes for efficient facet queries and filtering
    ensure_payload_indexes(client, collection)


def ensure_payload_indexes(client: QdrantClient, collection: str) -> None:
    """Create payload indexes required for facet queries and filtering.

    Idempotent — Qdrant silently ignores index creation if the index already
    exists with the same type.
    """
    index_fields = {
        "file_path": PayloadSchemaType.KEYWORD,
        "file_type": PayloadSchemaType.KEYWORD,
        "chunk_id": PayloadSchemaType.KEYWORD,
        "language": PayloadSchemaType.KEYWORD,
    }
    for field, schema_type in index_fields.items():
        try:
            client.create_payload_index(
                collection_name=collection,
                field_name=field,
                field_schema=schema_type,
            )
            logger.info("Created payload index: %s (%s)", field, schema_type)
        except Exception as e:
            # Index may already exist; log and continue
            logger.debug("Payload index %s skipped: %s", field, e)


def ingest(
    corpus_dir: Path,
    qdrant_url: str = "http://localhost:6333",
    embed_url: str = "http://localhost:8081",
    collection: str = "corpus",
    batch_size: int = 32,
    delete_missing: bool = False,
):
    """Run the full ingestion pipeline."""
    start = time.time()
    upsert_batch_size = 200

    client = QdrantClient(url=qdrant_url)

    # Ensure the collection exists before any upserts
    ensure_collection(client, collection)

    manifest_path = corpus_dir / ".airag_manifest.db"
    conn = open_manifest(manifest_path)

    # Scan files
    logger.info("Scanning %s ...", corpus_dir)
    files = scan_directory(corpus_dir)
    logger.info("Found %d files", len(files))

    # Delete stale sources if requested
    if delete_missing:
        current_paths = {str(f) for f in files}
        stale = list_stale_paths(conn, current_paths)
        for sp in stale:
            point_ids = delete_source(conn, sp)
            if point_ids:
                int_ids = [int(pid) for pid in point_ids]
                client.delete(collection_name=collection, points_selector=int_ids)
            logger.info("Deleted stale source: %s (%d chunks)", sp, len(point_ids))
        if stale:
            logger.info("Removed %d stale sources", len(stale))

    # Filter unchanged files
    new_files = []
    for f in files:
        fh = file_hash(f)
        src = get_source(conn, str(f))
        if src is None or src["content_hash"] != fh:
            new_files.append((f, fh))

    if not new_files:
        logger.info("No new or changed files. Nothing to do.")
        conn.close()
        return

    logger.info(
        "Processing %d new/changed files (skipping %d unchanged)",
        len(new_files),
        len(files) - len(new_files),
    )

    # Streaming per-file loop: chunk → embed → upsert → record
    total_chunks = 0
    total_files = 0

    embed_client = httpx.Client(timeout=120.0)
    try:
        for path, fh in tqdm(new_files, desc="Ingesting", file=sys.stderr):
            try:
                chunks = chunk_file(path)
            except Exception as e:
                logger.warning("Failed to chunk %s: %s", path, e)
                continue

            if not chunks:
                continue

            # Delete old Qdrant points if file was previously ingested
            old_point_ids = delete_source(conn, str(path))
            if old_point_ids:
                int_ids = [int(pid) for pid in old_point_ids]
                client.delete(collection_name=collection, points_selector=int_ids)

            # Embed this file's chunks in batches
            file_vectors = []
            texts = [c["text"] for c in chunks]
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                vectors = embed_batch(batch, embed_url, embed_client)
                file_vectors.extend(vectors)

            # Upsert this file's points to Qdrant
            chunk_ids = []
            point_ids = []
            for j in range(0, len(chunks), upsert_batch_size):
                batch_chunks = chunks[j : j + upsert_batch_size]
                batch_vectors = file_vectors[j : j + upsert_batch_size]
                points = []
                for chunk, vector in zip(batch_chunks, batch_vectors):
                    point_id = int(
                        hashlib.sha256(chunk["chunk_id"].encode()).hexdigest()[:16], 16
                    ) % (2**63)
                    rel_path = os.path.relpath(chunk["file_path"], corpus_dir)
                    payload = {
                        "chunk_id": chunk["chunk_id"],
                        "file_path": rel_path,
                        "file_type": chunk["file_type"],
                        "language": chunk.get("language"),
                        "symbol": chunk.get("symbol"),
                        "heading_path": chunk.get("heading_path"),
                        "json_path": chunk.get("json_path"),
                        "chunk_index": chunk["chunk_index"],
                        "token_count": chunk["token_count"],
                        "text": chunk["text"],
                    }
                    points.append(PointStruct(id=point_id, vector=vector, payload=payload))
                    chunk_ids.append(chunk["chunk_id"])
                    point_ids.append(str(point_id))
                client.upsert(collection_name=collection, points=points)

            # Record in manifest
            upsert_source(conn, str(path), fh, chunks[0]["file_type"], chunk_ids, point_ids)
            total_chunks += len(chunks)
            total_files += 1
    finally:
        embed_client.close()
        conn.close()

    elapsed = time.time() - start
    logger.info(
        "Ingestion complete: %d files, %d chunks, %.1f seconds",
        total_files,
        total_chunks,
        elapsed,
    )


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into airag corpus")
    parser.add_argument(
        "--corpus-dir", type=Path, required=True, help="Directory to ingest"
    )
    parser.add_argument(
        "--qdrant-url", default=os.environ.get("QDRANT_URL", "http://localhost:6333")
    )
    parser.add_argument(
        "--embed-url", default=os.environ.get("TEI_EMBED_URL", "http://localhost:8081")
    )
    parser.add_argument("--collection", default="corpus")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--delete-missing",
        action="store_true",
        help="Remove sources from manifest and Qdrant that no longer exist on disk",
    )
    args = parser.parse_args()

    ingest(
        corpus_dir=args.corpus_dir.resolve(),
        qdrant_url=args.qdrant_url,
        embed_url=args.embed_url,
        collection=args.collection,
        batch_size=args.batch_size,
        delete_missing=args.delete_missing,
    )


if __name__ == "__main__":
    main()
