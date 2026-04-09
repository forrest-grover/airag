"""HTML/XML parser and chunker — extract text content, strip tags, chunk."""

import logging

from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

from airag.chunking.code import count_tokens, make_chunk_id

logger = logging.getLogger("airag")

MARKUP_MAX_TOKENS = 512
MARKUP_OVERLAP = 64


def parse_markup(html: str, parser: str = "lxml") -> str:
    """Extract text from HTML/XML, stripping tags.

    Args:
        html: Raw HTML/XML string.
        parser: BeautifulSoup parser to use.

    Returns:
        Cleaned text content.
    """
    try:
        soup = BeautifulSoup(html, parser)
    except Exception:
        # Fall back to html.parser if lxml fails
        soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style"]):
        element.decompose()

    return soup.get_text(separator="\n", strip=True)


def chunk_markup(text: str, file_path: str) -> list[dict]:
    """Chunk markup (HTML/XML) after extracting text content.

    Args:
        text: Raw HTML/XML content.
        file_path: Absolute file path.

    Returns:
        List of chunk dicts.
    """
    clean_text = parse_markup(text)

    if not clean_text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MARKUP_MAX_TOKENS,
        chunk_overlap=MARKUP_OVERLAP,
        length_function=count_tokens,
        separators=["\n\n", "\n", " ", ""],
    )

    tokens = count_tokens(clean_text)
    if tokens <= MARKUP_MAX_TOKENS:
        parts = [clean_text]
    else:
        parts = splitter.split_text(clean_text)

    chunks = []
    byte_offset = 0

    for i, part in enumerate(parts):
        chunks.append({
            "chunk_id": make_chunk_id(file_path, byte_offset),
            "file_path": file_path,
            "file_type": "markup",
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
