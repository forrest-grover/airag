"""Code file parser and chunker — reads source, detects language, chunks via tree-sitter or fallback."""

import hashlib
import importlib
import logging
from pathlib import Path

import tree_sitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tokenizers import Tokenizer

logger = logging.getLogger("airag")

# Resolve the Qwen3 tokenizer from the local HuggingFace model cache.
# Layout: .volumes/models/models--Qwen--Qwen3-Embedding-0.6B/snapshots/<hash>/tokenizer.json
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MODEL_CACHE = _PROJECT_ROOT / ".volumes" / "models"
_QWEN3_REPO = _MODEL_CACHE / "models--Qwen--Qwen3-Embedding-0.6B"


def _resolve_tokenizer() -> Tokenizer:
    """Load Qwen3-Embedding-0.6B tokenizer from local HuggingFace cache."""
    refs_file = _QWEN3_REPO / "refs" / "main"
    snapshot_hash = refs_file.read_text().strip()
    tokenizer_path = _QWEN3_REPO / "snapshots" / snapshot_hash / "tokenizer.json"
    return Tokenizer.from_file(str(tokenizer_path))


_enc = _resolve_tokenizer()

CODE_MAX_TOKENS = 1024
CODE_OVERLAP = 128

# tree-sitter language modules — imported lazily
TREE_SITTER_LANGUAGES: dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "go": "tree_sitter_go",
    "rust": "tree_sitter_rust",
    "java": "tree_sitter_java",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
    "ruby": "tree_sitter_ruby",
    "bash": "tree_sitter_bash",
}

DEFINITION_NODE_TYPES = {
    "function_definition",
    "function_declaration",
    "function_item",
    "class_definition",
    "class_declaration",
    "class_specifier",
    "method_definition",
    "method_declaration",
    "method",
    "impl_item",
    "struct_item",
    "struct_specifier",
    "interface_declaration",
    "type_declaration",
    "module",
    "enum_item",
    "export_statement",
    "decorated_definition",
}


def has_tree_sitter_support(language: str | None) -> bool:
    """Check if tree-sitter grammar is available for the language."""
    return language in TREE_SITTER_LANGUAGES


def count_tokens(text: str) -> int:
    """Count tokens using the Qwen3-Embedding-0.6B tokenizer."""
    return len(_enc.encode(text).ids)


def make_chunk_id(file_path: str, byte_offset: int) -> str:
    """Generate deterministic chunk ID from file path and byte offset."""
    key = f"{file_path}:{byte_offset}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _get_ts_language(language: str):
    """Get tree-sitter Language for a language name."""
    module_name = TREE_SITTER_LANGUAGES.get(language)
    if not module_name:
        return None
    try:
        mod = importlib.import_module(module_name)
        # Some modules (like typescript) expose .language_typescript()
        if language == "typescript" and hasattr(mod, "language_typescript"):
            return tree_sitter.Language(mod.language_typescript())
        return tree_sitter.Language(mod.language())
    except Exception:
        logger.warning("Failed to load tree-sitter for %s", language)
        return None


def _get_parser(language: str):
    """Get a tree-sitter parser for the given language."""
    parser = tree_sitter.Parser()
    lang = _get_ts_language(language)
    if lang is None:
        return None
    parser.language = lang
    return parser


def _get_symbol_name(node) -> str | None:
    """Extract the name/identifier from a definition node."""
    for child in node.children:
        if child.type in (
            "identifier",
            "name",
            "type_identifier",
            "property_identifier",
        ):
            return child.text.decode("utf-8")
        # For decorated_definition or export_statement, look deeper
        if child.type in DEFINITION_NODE_TYPES:
            return _get_symbol_name(child)
    return None


def _make_context_header(file_path: str, language: str | None) -> str:
    """Build context header prepended to each code chunk."""
    lines = [f"# file: {file_path}"]
    if language:
        lines.append(f"# language: {language}")
    return "\n".join(lines) + "\n"


def _make_splitter(max_tokens: int, overlap: int) -> RecursiveCharacterTextSplitter:
    """Create a RecursiveCharacterTextSplitter using token-based length."""
    return RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=overlap,
        length_function=count_tokens,
        separators=["\n\n", "\n", " ", ""],
    )


def _split_large_text(text: str, max_tokens: int, overlap: int) -> list[str]:
    """Split text that exceeds max_tokens using RecursiveCharacterTextSplitter."""
    splitter = _make_splitter(max_tokens, overlap)
    return splitter.split_text(text)


def _chunks_from_segments(
    segments: list[dict],
    file_path: str,
    language: str | None,
    source_bytes: bytes,
) -> list[dict]:
    """Convert segments into chunk dicts with metadata.

    Each segment has keys: text, byte_offset, symbol (optional).
    """
    header = _make_context_header(file_path, language)
    header_tokens = count_tokens(header)
    effective_max = CODE_MAX_TOKENS - header_tokens

    chunks = []
    chunk_index = 0

    for seg in segments:
        seg_text = seg["text"]
        seg_tokens = count_tokens(seg_text)
        symbol = seg.get("symbol")

        if seg_tokens <= effective_max:
            full_text = header + seg_text
            chunks.append(
                {
                    "chunk_id": make_chunk_id(file_path, seg["byte_offset"]),
                    "file_path": file_path,
                    "file_type": "code",
                    "language": language,
                    "symbol": symbol,
                    "heading_path": None,
                    "json_path": None,
                    "chunk_index": chunk_index,
                    "token_count": count_tokens(full_text),
                    "text": full_text,
                }
            )
            chunk_index += 1
        else:
            # Split large segment
            sub_parts = _split_large_text(seg_text, effective_max, CODE_OVERLAP)
            for i, part in enumerate(sub_parts):
                # Approximate byte offset for sub-parts
                part_byte_offset = seg["byte_offset"] + (
                    i * len(part.encode("utf-8")) // 2
                )
                full_text = header + part
                chunks.append(
                    {
                        "chunk_id": make_chunk_id(file_path, part_byte_offset),
                        "file_path": file_path,
                        "file_type": "code",
                        "language": language,
                        "symbol": symbol,
                        "heading_path": None,
                        "json_path": None,
                        "chunk_index": chunk_index,
                        "token_count": count_tokens(full_text),
                        "text": full_text,
                    }
                )
                chunk_index += 1

    return chunks


def chunk_code(text: str, file_path: str, language: str | None) -> list[dict]:
    """Chunk code file using tree-sitter AST when available, fallback to text splitting.

    Args:
        text: Source code content.
        file_path: Absolute file path.
        language: Programming language name or None.

    Returns:
        List of chunk dicts.
    """
    if language and has_tree_sitter_support(language):
        parser = _get_parser(language)
        if parser is not None:
            return _chunk_with_tree_sitter(text, file_path, language, parser)

    # Fallback: no tree-sitter support
    return _chunk_code_fallback(text, file_path, language)


def _chunk_with_tree_sitter(
    text: str, file_path: str, language: str | None, parser
) -> list[dict]:
    """Chunk code using tree-sitter AST."""
    source_bytes = text.encode("utf-8")
    tree = parser.parse(source_bytes)
    root = tree.root_node

    segments: list[dict] = []
    inter_def_start = 0  # byte offset tracking for inter-definition code

    for child in root.children:
        child_start = child.start_byte
        child_end = child.end_byte

        if child.type in DEFINITION_NODE_TYPES:
            # Collect inter-definition code before this node
            if child_start > inter_def_start:
                inter_text = (
                    source_bytes[inter_def_start:child_start]
                    .decode("utf-8", errors="replace")
                    .strip()
                )
                if inter_text:
                    segments.append(
                        {
                            "text": inter_text,
                            "byte_offset": inter_def_start,
                            "symbol": None,
                        }
                    )

            # Collect the definition itself
            def_text = source_bytes[child_start:child_end].decode(
                "utf-8", errors="replace"
            )
            symbol = _get_symbol_name(child)
            segments.append(
                {
                    "text": def_text,
                    "byte_offset": child_start,
                    "symbol": symbol,
                }
            )
            inter_def_start = child_end
        else:
            # Not a definition — will be collected as inter-definition code
            continue

    # Trailing inter-definition code
    if inter_def_start < len(source_bytes):
        trailing = (
            source_bytes[inter_def_start:].decode("utf-8", errors="replace").strip()
        )
        if trailing:
            segments.append(
                {
                    "text": trailing,
                    "byte_offset": inter_def_start,
                    "symbol": None,
                }
            )

    if not segments:
        # No definitions found — treat entire file as one segment
        segments.append({"text": text, "byte_offset": 0, "symbol": None})

    return _chunks_from_segments(segments, file_path, language, source_bytes)


def _chunk_code_fallback(text: str, file_path: str, language: str | None) -> list[dict]:
    """Chunk code without tree-sitter using text splitting."""
    header = _make_context_header(file_path, language)
    header_tokens = count_tokens(header)
    effective_max = CODE_MAX_TOKENS - header_tokens

    parts = _split_large_text(text, effective_max, CODE_OVERLAP)
    chunks = []

    byte_offset = 0
    for i, part in enumerate(parts):
        full_text = header + part
        chunks.append(
            {
                "chunk_id": make_chunk_id(file_path, byte_offset),
                "file_path": file_path,
                "file_type": "code",
                "language": language,
                "symbol": None,
                "heading_path": None,
                "json_path": None,
                "chunk_index": i,
                "token_count": count_tokens(full_text),
                "text": full_text,
            }
        )
        byte_offset += len(part.encode("utf-8"))

    return chunks


def chunk_text_fallback(text: str, file_path: str, file_type: str) -> list[dict]:
    """Chunk plain text files using RecursiveCharacterTextSplitter.

    Parameters: 512 max tokens, 64 overlap.
    """
    max_tokens = 512
    overlap = 64

    parts = _split_large_text(text, max_tokens, overlap)
    chunks = []

    byte_offset = 0
    for i, part in enumerate(parts):
        chunks.append(
            {
                "chunk_id": make_chunk_id(file_path, byte_offset),
                "file_path": file_path,
                "file_type": file_type,
                "language": None,
                "symbol": None,
                "heading_path": None,
                "json_path": None,
                "chunk_index": i,
                "token_count": count_tokens(part),
                "text": part,
            }
        )
        byte_offset += len(part.encode("utf-8"))

    return chunks
