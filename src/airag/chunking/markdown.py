"""Markdown parser and chunker — preserves heading hierarchy."""

import logging
import re

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from airag.chunking.code import count_tokens, make_chunk_id

logger = logging.getLogger("airag")

MD_MAX_TOKENS = 512
MD_OVERLAP = 64


def extract_headings(text: str) -> list[dict]:
    """Extract heading hierarchy from markdown text.

    Returns:
        List of dicts with keys: level, title, line
    """
    lines = text.split("\n")
    headings: list[dict] = []

    for i, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            headings.append({
                "level": len(match.group(1)),
                "title": match.group(2).strip(),
                "line": i,
            })

    return headings


def get_heading_path(headings: list[dict], line: int) -> str:
    """Build a heading path for a given line number.

    Returns heading breadcrumb like "Title > Section A > Subsection".
    """
    path: list[str] = []
    current_levels: dict[int, str] = {}

    for h in headings:
        if h["line"] > line:
            break
        current_levels[h["level"]] = h["title"]
        # Clear lower-level headings
        for level in list(current_levels):
            if level > h["level"]:
                del current_levels[level]

    for level in sorted(current_levels):
        path.append(current_levels[level])

    return " > ".join(path) if path else ""


def chunk_markdown(text: str, file_path: str) -> list[dict]:
    """Chunk markdown by headings, then sub-split large sections.

    Args:
        text: Markdown content.
        file_path: Absolute file path.

    Returns:
        List of chunk dicts.
    """
    headers_to_split = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
    ]

    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split,
        strip_headers=False,
    )

    sub_splitter = RecursiveCharacterTextSplitter(
        chunk_size=MD_MAX_TOKENS,
        chunk_overlap=MD_OVERLAP,
        length_function=count_tokens,
        separators=["\n\n", "\n", " ", ""],
    )

    sections = md_splitter.split_text(text)

    chunks = []
    chunk_index = 0
    # Track byte offset for chunk_id generation
    byte_offset = 0

    for section in sections:
        section_text = section.page_content
        # Build heading path from section metadata
        heading_parts = []
        for key in ("h1", "h2", "h3", "h4"):
            if key in section.metadata:
                heading_parts.append(section.metadata[key])
        heading_path = " > ".join(heading_parts) if heading_parts else None

        section_tokens = count_tokens(section_text)

        if section_tokens <= MD_MAX_TOKENS:
            chunks.append({
                "chunk_id": make_chunk_id(file_path, byte_offset),
                "file_path": file_path,
                "file_type": "markdown",
                "language": None,
                "symbol": None,
                "heading_path": heading_path,
                "json_path": None,
                "chunk_index": chunk_index,
                "token_count": section_tokens,
                "text": section_text,
            })
            chunk_index += 1
            byte_offset += len(section_text.encode("utf-8"))
        else:
            # Sub-split large section
            sub_parts = sub_splitter.split_text(section_text)
            for part in sub_parts:
                chunks.append({
                    "chunk_id": make_chunk_id(file_path, byte_offset),
                    "file_path": file_path,
                    "file_type": "markdown",
                    "language": None,
                    "symbol": None,
                    "heading_path": heading_path,
                    "json_path": None,
                    "chunk_index": chunk_index,
                    "token_count": count_tokens(part),
                    "text": part,
                })
                chunk_index += 1
                byte_offset += len(part.encode("utf-8"))

    # Handle edge case: empty or no-heading markdown
    if not chunks:
        parts = sub_splitter.split_text(text) if count_tokens(text) > MD_MAX_TOKENS else [text]
        for i, part in enumerate(parts):
            chunks.append({
                "chunk_id": make_chunk_id(file_path, byte_offset),
                "file_path": file_path,
                "file_type": "markdown",
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
