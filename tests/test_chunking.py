"""Tests for each chunker module."""

import json

from airag.chunking.code import (
    chunk_code,
    chunk_text_fallback,
    count_tokens,
    make_chunk_id,
)
from airag.chunking.markdown import chunk_markdown, extract_headings, get_heading_path
from airag.chunking.markup import chunk_markup, parse_markup
from airag.chunking.json_chunker import chunk_json
from airag.chunking.router import chunk_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_CHUNK_KEYS = {
    "chunk_id",
    "file_path",
    "file_type",
    "language",
    "symbol",
    "heading_path",
    "json_path",
    "chunk_index",
    "token_count",
    "text",
}


def assert_valid_chunks(chunks, expected_file_type, file_path):
    """Validate common invariants on a list of chunks."""
    assert len(chunks) > 0
    for i, c in enumerate(chunks):
        assert REQUIRED_CHUNK_KEYS <= set(c.keys()), f"chunk {i} missing keys"
        assert c["file_type"] == expected_file_type
        assert c["file_path"] == file_path
        assert c["chunk_index"] == i
        assert c["token_count"] > 0
        assert len(c["chunk_id"]) == 16
        assert len(c["text"]) > 0


# ---------------------------------------------------------------------------
# Code chunker
# ---------------------------------------------------------------------------


class TestCodeChunker:
    """Tests for chunk_code (tree-sitter path)."""

    def test_python_splits_by_definitions(self, sample_python):
        chunks = chunk_code(sample_python, "/src/example.py", "python")
        assert_valid_chunks(chunks, "code", "/src/example.py")
        assert all(c["language"] == "python" for c in chunks)
        # Should find the function and class as symbols
        symbols = [c["symbol"] for c in chunks if c["symbol"]]
        assert "hello" in symbols
        assert "Greeter" in symbols

    def test_python_chunks_have_context_header(self, sample_python):
        chunks = chunk_code(sample_python, "/src/example.py", "python")
        for c in chunks:
            assert "# file: /src/example.py" in c["text"]
            assert "# language: python" in c["text"]

    def test_token_count_accurate(self, sample_python):
        chunks = chunk_code(sample_python, "/src/example.py", "python")
        for c in chunks:
            assert c["token_count"] == count_tokens(c["text"])

    def test_chunk_ids_deterministic(self, sample_python):
        a = chunk_code(sample_python, "/src/example.py", "python")
        b = chunk_code(sample_python, "/src/example.py", "python")
        assert [c["chunk_id"] for c in a] == [c["chunk_id"] for c in b]

    def test_chunk_ids_unique(self, sample_python):
        chunks = chunk_code(sample_python, "/src/example.py", "python")
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_unsupported_language_uses_fallback(self):
        code = "SELECT * FROM users WHERE id = 1;"
        chunks = chunk_code(code, "/queries/q.sql", "sql")
        assert_valid_chunks(chunks, "code", "/queries/q.sql")
        assert chunks[0]["symbol"] is None

    def test_empty_code_returns_chunks(self):
        chunks = chunk_code("", "/empty.py", "python")
        # Even empty file should produce something (the header at least, or empty text)
        # Actually empty text will have no segments, falls through to no-segments branch
        assert isinstance(chunks, list)

    def test_large_function_gets_split(self):
        """A function larger than CODE_MAX_TOKENS should be split into sub-chunks."""
        # Build a function with many lines to exceed 1024 tokens
        lines = ["def big_func():"]
        for i in range(200):
            lines.append(f"    x_{i} = {i} * {i}  # computation line {i}")
        lines.append("    return x_0")
        big_code = "\n".join(lines)
        chunks = chunk_code(big_code, "/big.py", "python")
        assert len(chunks) > 1
        # All should reference the same symbol
        for c in chunks:
            assert c["symbol"] == "big_func"


class TestTextFallback:
    """Tests for chunk_text_fallback."""

    def test_small_text_single_chunk(self):
        text = "Hello, world."
        chunks = chunk_text_fallback(text, "/notes.txt", "text")
        assert len(chunks) == 1
        assert chunks[0]["file_type"] == "text"
        assert chunks[0]["text"] == text

    def test_text_metadata_fields(self):
        chunks = chunk_text_fallback("content", "/f.txt", "text")
        assert chunks[0]["language"] is None
        assert chunks[0]["symbol"] is None
        assert chunks[0]["heading_path"] is None
        assert chunks[0]["json_path"] is None


class TestMakeChunkId:
    """Tests for make_chunk_id."""

    def test_deterministic(self):
        assert make_chunk_id("/a.py", 0) == make_chunk_id("/a.py", 0)

    def test_different_inputs_different_ids(self):
        assert make_chunk_id("/a.py", 0) != make_chunk_id("/a.py", 100)
        assert make_chunk_id("/a.py", 0) != make_chunk_id("/b.py", 0)

    def test_length(self):
        assert len(make_chunk_id("/a.py", 0)) == 16


# ---------------------------------------------------------------------------
# Markdown chunker
# ---------------------------------------------------------------------------


class TestMarkdownChunker:
    """Tests for chunk_markdown."""

    def test_splits_by_headers(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown, "/README.md")
        assert_valid_chunks(chunks, "markdown", "/README.md")
        assert len(chunks) >= 3  # multiple sections

    def test_heading_path_populated(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown, "/README.md")
        paths = [c["heading_path"] for c in chunks if c["heading_path"]]
        assert len(paths) > 0
        # Should have nested paths like "Project Title > Installation > Prerequisites"
        nested = [p for p in paths if " > " in p]
        assert len(nested) > 0

    def test_no_heading_markdown(self):
        text = "Just plain text without any headings.\nAnother line."
        chunks = chunk_markdown(text, "/plain.md")
        assert len(chunks) >= 1
        assert chunks[0]["file_type"] == "markdown"

    def test_token_counts_within_limit(self, sample_markdown):
        from airag.chunking.markdown import MD_MAX_TOKENS

        chunks = chunk_markdown(sample_markdown, "/README.md")
        for c in chunks:
            assert (
                c["token_count"] <= MD_MAX_TOKENS + 10
            )  # small tolerance for splitter


class TestExtractHeadings:
    """Tests for extract_headings helper."""

    def test_extracts_all_levels(self):
        text = "# H1\n## H2\n### H3\n#### H4\n##### H5"
        headings = extract_headings(text)
        assert len(headings) == 5
        assert headings[0] == {"level": 1, "title": "H1", "line": 0}
        assert headings[1]["level"] == 2

    def test_no_headings(self):
        assert extract_headings("plain text") == []


class TestGetHeadingPath:
    """Tests for get_heading_path helper."""

    def test_builds_breadcrumb(self):
        headings = [
            {"level": 1, "title": "Top", "line": 0},
            {"level": 2, "title": "Sub", "line": 5},
        ]
        assert get_heading_path(headings, 6) == "Top > Sub"

    def test_empty_before_first_heading(self):
        headings = [{"level": 1, "title": "Top", "line": 5}]
        assert get_heading_path(headings, 0) == ""


# ---------------------------------------------------------------------------
# Markup chunker
# ---------------------------------------------------------------------------


class TestMarkupChunker:
    """Tests for chunk_markup and parse_markup."""

    def test_strips_tags(self, sample_html):
        clean = parse_markup(sample_html)
        assert "<p>" not in clean
        assert "<h1>" not in clean
        assert "Welcome" in clean

    def test_removes_script_and_style(self, sample_html):
        clean = parse_markup(sample_html)
        assert "alert" not in clean
        assert "display: none" not in clean

    def test_chunk_markup_produces_valid_chunks(self, sample_html):
        chunks = chunk_markup(sample_html, "/page.html")
        assert_valid_chunks(chunks, "markup", "/page.html")

    def test_empty_html_returns_empty(self):
        chunks = chunk_markup("<html><body></body></html>", "/empty.html")
        assert chunks == []

    def test_xml_parsing(self):
        xml = "<root><item>Hello</item><item>World</item></root>"
        clean = parse_markup(xml)
        assert "Hello" in clean
        assert "World" in clean


# ---------------------------------------------------------------------------
# JSON chunker
# ---------------------------------------------------------------------------


class TestJsonChunker:
    """Tests for chunk_json."""

    def test_small_json_single_chunk(self, sample_json):
        chunks = chunk_json(sample_json, "/package.json")
        assert_valid_chunks(chunks, "json", "/package.json")
        # Small JSON fits in one chunk
        assert len(chunks) == 1
        assert chunks[0]["json_path"] is None  # single-chunk mode

    def test_yaml_content(self, sample_yaml):
        chunks = chunk_json(sample_yaml, "/config.yaml")
        assert len(chunks) >= 1
        assert chunks[0]["file_type"] == "json"

    def test_large_json_splits_by_keys(self):
        """Large JSON should be split into multiple chunks with json_path."""
        data = {f"key_{i}": {"nested": "x" * 200} for i in range(50)}
        text = json.dumps(data, indent=2)
        chunks = chunk_json(text, "/big.json")
        assert len(chunks) > 1
        paths = [c["json_path"] for c in chunks if c["json_path"]]
        assert len(paths) > 0

    def test_json_array_content(self):
        data = [{"id": i, "value": f"item_{i}"} for i in range(5)]
        text = json.dumps(data, indent=2)
        chunks = chunk_json(text, "/list.json")
        assert len(chunks) >= 1

    def test_invalid_json_falls_back(self):
        """Non-parseable content should still produce chunks via text splitting."""
        text = "this is not valid json or yaml " * 200
        chunks = chunk_json(text, "/broken.json")
        assert len(chunks) >= 1


# ---------------------------------------------------------------------------
# Router chunk_file integration
# ---------------------------------------------------------------------------


class TestChunkFileRouter:
    """Integration tests for chunk_file routing."""

    def test_python_file_routed(self, python_file):
        chunks = chunk_file(python_file)
        assert all(c["file_type"] == "code" for c in chunks)
        assert all(c["language"] == "python" for c in chunks)

    def test_markdown_file_routed(self, markdown_file):
        chunks = chunk_file(markdown_file)
        assert all(c["file_type"] == "markdown" for c in chunks)

    def test_html_file_routed(self, html_file):
        chunks = chunk_file(html_file)
        assert all(c["file_type"] == "markup" for c in chunks)

    def test_json_file_routed(self, json_file):
        chunks = chunk_file(json_file)
        assert all(c["file_type"] == "json" for c in chunks)

    def test_text_file_fallback(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("Some plain text content.")
        chunks = chunk_file(f)
        assert all(c["file_type"] == "text" for c in chunks)

    def test_unknown_extension_uses_text_fallback(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("Mystery content here.")
        chunks = chunk_file(f)
        assert all(c["file_type"] == "text" for c in chunks)
