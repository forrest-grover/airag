"""Parse, chunk, embed, and upsert pipeline."""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from tqdm import tqdm

from airag.chunking import chunk_file

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("airag")

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
    if path.is_dir() and path.name in SKIP_PATTERNS:
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


def embed_batch(texts: list[str], embed_url: str) -> list[list[float]]:
    """Embed a batch of texts via TEI synchronously."""
    with httpx.Client(timeout=60.0) as client:
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


def ingest(
    corpus_dir: Path,
    qdrant_url: str = "http://localhost:6333",
    embed_url: str = "http://localhost:8081",
    collection: str = "corpus",
    batch_size: int = 32,
):
    """Run the full ingestion pipeline."""
    start = time.time()

    client = QdrantClient(url=qdrant_url)
    state_path = corpus_dir / ".airag_state.json"
    state = load_state(state_path)

    # Scan files
    logger.info("Scanning %s ...", corpus_dir)
    files = scan_directory(corpus_dir)
    logger.info("Found %d files", len(files))

    # Filter unchanged files
    new_files = []
    for f in files:
        fh = file_hash(f)
        if state.get(str(f)) != fh:
            new_files.append((f, fh))

    if not new_files:
        logger.info("No new or changed files. Nothing to do.")
        return

    logger.info(
        "Processing %d new/changed files (skipping %d unchanged)",
        len(new_files),
        len(files) - len(new_files),
    )

    # Process files: parse + chunk
    all_chunks = []
    for path, fh in tqdm(new_files, desc="Chunking", file=sys.stderr):
        try:
            chunks = chunk_file(path)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.warning("Failed to chunk %s: %s", path, e)
            continue

    logger.info("Generated %d chunks from %d files", len(all_chunks), len(new_files))

    if not all_chunks:
        logger.info("No chunks generated. Nothing to upsert.")
        return

    # Embed in batches
    logger.info("Embedding %d chunks in batches of %d ...", len(all_chunks), batch_size)
    all_vectors = []
    texts = [c["text"] for c in all_chunks]

    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding", file=sys.stderr):
        batch = texts[i : i + batch_size]
        try:
            vectors = embed_batch(batch, embed_url)
            all_vectors.extend(vectors)
        except Exception as e:
            logger.error("Embedding failed at batch %d: %s", i // batch_size, e)
            raise

    # Upsert to Qdrant in batches
    logger.info("Upserting %d points to Qdrant ...", len(all_chunks))
    upsert_batch_size = 100

    for i in tqdm(
        range(0, len(all_chunks), upsert_batch_size), desc="Upserting", file=sys.stderr
    ):
        batch_chunks = all_chunks[i : i + upsert_batch_size]
        batch_vectors = all_vectors[i : i + upsert_batch_size]

        points = []
        for j, (chunk, vector) in enumerate(zip(batch_chunks, batch_vectors)):
            # Use chunk_id as a UUID-like identifier
            # Qdrant needs int or UUID ids — use hash
            point_id = int(
                hashlib.sha256(chunk["chunk_id"].encode()).hexdigest()[:16], 16
            ) % (2**63)

            # Store paths relative to corpus dir to avoid leaking absolute paths
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

        client.upsert(collection_name=collection, points=points)

    # Update state
    for path, fh in new_files:
        state[str(path)] = fh
    save_state(state_path, state)

    elapsed = time.time() - start
    logger.info(
        "Ingestion complete: %d files, %d chunks, %.1f seconds",
        len(new_files),
        len(all_chunks),
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
    args = parser.parse_args()

    ingest(
        corpus_dir=args.corpus_dir.resolve(),
        qdrant_url=args.qdrant_url,
        embed_url=args.embed_url,
        collection=args.collection,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
