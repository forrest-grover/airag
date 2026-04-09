"""File type detection, dispatch to appropriate parser, and chunk_file orchestration."""

import logging
from pathlib import Path

logger = logging.getLogger("airag")

__all__ = ["detect_file_type", "parse_file", "chunk_file"]

# Extension → (file_type, language|None)
EXTENSION_MAP: dict[str, tuple[str, str | None]] = {
    # Code
    ".py": ("code", "python"),
    ".js": ("code", "javascript"),
    ".jsx": ("code", "javascript"),
    ".ts": ("code", "typescript"),
    ".tsx": ("code", "typescript"),
    ".go": ("code", "go"),
    ".rs": ("code", "rust"),
    ".java": ("code", "java"),
    ".c": ("code", "c"),
    ".h": ("code", "c"),
    ".cpp": ("code", "cpp"),
    ".hpp": ("code", "cpp"),
    ".cc": ("code", "cpp"),
    ".rb": ("code", "ruby"),
    ".sh": ("code", "bash"),
    ".bash": ("code", "bash"),
    ".sql": ("code", "sql"),
    ".css": ("code", "css"),
    ".scss": ("code", "css"),
    # Markdown
    ".md": ("markdown", None),
    ".mdx": ("markdown", None),
    # Markup
    ".html": ("markup", None),
    ".htm": ("markup", None),
    ".xml": ("markup", None),
    ".svg": ("markup", None),
    # JSON/YAML/TOML
    ".json": ("json", None),
    ".jsonl": ("json", None),
    ".yaml": ("json", None),
    ".yml": ("json", None),
    ".toml": ("json", None),
    # Plain text
    ".txt": ("text", None),
    ".rst": ("text", None),
    ".log": ("text", None),
    ".csv": ("text", None),
    ".env": ("text", None),
    ".cfg": ("text", None),
    ".ini": ("text", None),
    ".conf": ("text", None),
    # Config files without extension handled by name
}

# Filenames without extensions
FILENAME_MAP: dict[str, tuple[str, str | None]] = {
    "Makefile": ("code", "makefile"),
    "Dockerfile": ("code", "dockerfile"),
    "Jenkinsfile": ("code", "groovy"),
    ".gitignore": ("text", None),
    ".dockerignore": ("text", None),
    ".editorconfig": ("text", None),
    "LICENSE": ("text", None),
    "README": ("text", None),
}


def detect_file_type(path: Path) -> tuple[str, str | None]:
    """Detect file type and language from path.

    Returns:
        Tuple of (file_type, language). file_type is one of:
        "code", "markdown", "markup", "json", "text".
        language is the programming language or None.
    """
    # Check filename first (for extensionless files)
    if path.name in FILENAME_MAP:
        return FILENAME_MAP[path.name]

    # Check extension
    suffix = path.suffix.lower()
    if suffix in EXTENSION_MAP:
        return EXTENSION_MAP[suffix]

    # Default to text
    logger.debug("Unknown extension %s for %s, defaulting to text", suffix, path)
    return ("text", None)


def parse_file(path: Path) -> dict:
    """Parse a file and return its content with metadata.

    Returns:
        Dict with keys: text, file_path, file_type, language
    """
    file_type, language = detect_file_type(path)

    text = path.read_text(encoding="utf-8", errors="replace")

    metadata = {
        "text": text,
        "file_path": str(path),
        "file_type": file_type,
        "language": language,
    }

    # For markup, strip tags and extract clean text as an alternative
    if file_type == "markup":
        from airag.chunking.markup import parse_markup

        metadata["parsed"] = parse_markup(text)

    return metadata


def chunk_file(path: Path) -> list[dict]:
    """Parse and chunk a file, returning a list of chunk dicts.

    Each chunk dict has keys: chunk_id, file_path, file_type, language,
    symbol, heading_path, json_path, chunk_index, token_count, text.
    """
    parsed = parse_file(path)
    file_type = parsed["file_type"]

    if file_type == "code":
        from airag.chunking.code import chunk_code

        return chunk_code(parsed["text"], parsed["file_path"], parsed["language"])
    elif file_type == "markdown":
        from airag.chunking.markdown import chunk_markdown

        return chunk_markdown(parsed["text"], parsed["file_path"])
    elif file_type == "markup":
        from airag.chunking.markup import chunk_markup

        return chunk_markup(parsed["text"], parsed["file_path"])
    elif file_type == "json":
        from airag.chunking.json_chunker import chunk_json

        return chunk_json(parsed["text"], parsed["file_path"])
    else:
        # text fallback
        from airag.chunking.code import chunk_text_fallback

        return chunk_text_fallback(parsed["text"], parsed["file_path"], file_type)
