"""JSON/YAML/TOML parser and chunker."""

import json
import logging
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from airag.chunking.code import count_tokens, make_chunk_id

logger = logging.getLogger("airag")

JSON_MAX_TOKENS = 1024
JSON_OVERLAP = 128


def parse_json_file(path: Path) -> dict:
    """Parse a JSON, YAML, or TOML file.

    Returns:
        Dict with keys: data (parsed object), format (json/yaml/toml), text
    """
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")

    if suffix in (".yaml", ".yml"):
        try:
            import yaml

            data = yaml.safe_load(text)
            return {"data": data, "format": "yaml", "text": text}
        except Exception:
            return {"data": None, "format": "yaml", "text": text}

    if suffix == ".toml":
        try:
            import tomllib

            data = tomllib.loads(text)
            return {"data": data, "format": "toml", "text": text}
        except Exception:
            return {"data": None, "format": "toml", "text": text}

    # JSON / JSONL
    try:
        data = json.loads(text)
        return {"data": data, "format": "json", "text": text}
    except json.JSONDecodeError:
        # Could be JSONL
        lines = []
        for line in text.strip().split("\n"):
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        if lines:
            return {"data": lines, "format": "jsonl", "text": text}
        return {"data": None, "format": "json", "text": text}


def _flatten_dict(data: dict, prefix: str = "") -> list[dict]:
    """Flatten a dict into key-path segments for chunking.

    Returns list of dicts with keys: json_path, text.
    """
    segments = []
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            # Serialize the sub-object
            text = json.dumps({key: value}, indent=2, ensure_ascii=False)
            tokens = count_tokens(text)
            if tokens <= JSON_MAX_TOKENS:
                segments.append({"json_path": path, "text": text})
            else:
                # Recurse into large sub-objects
                segments.extend(_flatten_dict(value, prefix=path))
        elif isinstance(value, list):
            text = json.dumps({key: value}, indent=2, ensure_ascii=False)
            tokens = count_tokens(text)
            if tokens <= JSON_MAX_TOKENS:
                segments.append({"json_path": path, "text": text})
            else:
                # Split list items individually
                for i, item in enumerate(value):
                    item_path = f"{path}[{i}]"
                    item_text = json.dumps(item, indent=2, ensure_ascii=False)
                    segments.append({"json_path": item_path, "text": item_text})
        else:
            text = json.dumps({key: value}, indent=2, ensure_ascii=False)
            segments.append({"json_path": path, "text": text})

    return segments


def chunk_json(text: str, file_path: str) -> list[dict]:
    """Chunk JSON/YAML/TOML content.

    If total text fits within token limit, return as single chunk.
    Otherwise, split by key paths for objects or by items for arrays.
    Falls back to text splitting if structured approach fails.

    Args:
        text: Raw file content (JSON/YAML/TOML text).
        file_path: Absolute file path.

    Returns:
        List of chunk dicts.
    """
    total_tokens = count_tokens(text)

    # Small enough for a single chunk
    if total_tokens <= JSON_MAX_TOKENS:
        return [{
            "chunk_id": make_chunk_id(file_path, 0),
            "file_path": file_path,
            "file_type": "json",
            "language": None,
            "symbol": None,
            "heading_path": None,
            "json_path": None,
            "chunk_index": 0,
            "token_count": total_tokens,
            "text": text,
        }]

    # Try structured splitting
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Try YAML
        try:
            import yaml
            data = yaml.safe_load(text)
        except Exception:
            # Try TOML
            try:
                import tomllib
                data = tomllib.loads(text)
            except Exception:
                data = None

    if data is not None:
        segments = _structured_split(data)
        if segments:
            return _segments_to_chunks(segments, file_path)

    # Fallback: text splitting
    return _text_split_json(text, file_path)


def _structured_split(data) -> list[dict]:
    """Split parsed data into segments with json_path metadata."""
    if isinstance(data, dict):
        return _flatten_dict(data)
    elif isinstance(data, list):
        segments = []
        for i, item in enumerate(data):
            item_text = json.dumps(item, indent=2, ensure_ascii=False)
            segments.append({"json_path": f"[{i}]", "text": item_text})
        return segments
    return []


def _segments_to_chunks(segments: list[dict], file_path: str) -> list[dict]:
    """Convert structured segments to chunk dicts, merging small segments."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=JSON_MAX_TOKENS,
        chunk_overlap=JSON_OVERLAP,
        length_function=count_tokens,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = []
    byte_offset = 0

    for i, seg in enumerate(segments):
        seg_text = seg["text"]
        seg_tokens = count_tokens(seg_text)

        if seg_tokens <= JSON_MAX_TOKENS:
            chunks.append({
                "chunk_id": make_chunk_id(file_path, byte_offset),
                "file_path": file_path,
                "file_type": "json",
                "language": None,
                "symbol": None,
                "heading_path": None,
                "json_path": seg["json_path"],
                "chunk_index": len(chunks),
                "token_count": seg_tokens,
                "text": seg_text,
            })
        else:
            # Sub-split oversized segments
            parts = splitter.split_text(seg_text)
            for part in parts:
                chunks.append({
                    "chunk_id": make_chunk_id(file_path, byte_offset),
                    "file_path": file_path,
                    "file_type": "json",
                    "language": None,
                    "symbol": None,
                    "heading_path": None,
                    "json_path": seg["json_path"],
                    "chunk_index": len(chunks),
                    "token_count": count_tokens(part),
                    "text": part,
                })
                byte_offset += len(part.encode("utf-8"))
                continue
        byte_offset += len(seg_text.encode("utf-8"))

    return chunks


def _text_split_json(text: str, file_path: str) -> list[dict]:
    """Fallback: split JSON text with RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=JSON_MAX_TOKENS,
        chunk_overlap=JSON_OVERLAP,
        length_function=count_tokens,
        separators=["\n\n", "\n", " ", ""],
    )

    parts = splitter.split_text(text)
    chunks = []
    byte_offset = 0

    for i, part in enumerate(parts):
        chunks.append({
            "chunk_id": make_chunk_id(file_path, byte_offset),
            "file_path": file_path,
            "file_type": "json",
            "language": None,
            "symbol": None,
            "heading_path": None,
            "json_path": None,
            "chunk_index": i,
            "token_count": count_tokens(part),
            "text": part,
        })
        byte_offset += len(part.encode("utf-8"))

    return chunks
