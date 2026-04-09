"""Tests for file type detection and parse_file routing."""

from airag.chunking.router import detect_file_type, parse_file


class TestDetectFileType:
    """Tests for detect_file_type."""

    def test_python_file(self, tmp_path):
        assert detect_file_type(tmp_path / "main.py") == ("code", "python")

    def test_javascript_file(self, tmp_path):
        assert detect_file_type(tmp_path / "app.js") == ("code", "javascript")

    def test_typescript_file(self, tmp_path):
        assert detect_file_type(tmp_path / "app.ts") == ("code", "typescript")

    def test_go_file(self, tmp_path):
        assert detect_file_type(tmp_path / "main.go") == ("code", "go")

    def test_rust_file(self, tmp_path):
        assert detect_file_type(tmp_path / "lib.rs") == ("code", "rust")

    def test_markdown_file(self, tmp_path):
        assert detect_file_type(tmp_path / "README.md") == ("markdown", None)

    def test_mdx_file(self, tmp_path):
        assert detect_file_type(tmp_path / "page.mdx") == ("markdown", None)

    def test_html_file(self, tmp_path):
        assert detect_file_type(tmp_path / "index.html") == ("markup", None)

    def test_xml_file(self, tmp_path):
        assert detect_file_type(tmp_path / "data.xml") == ("markup", None)

    def test_json_file(self, tmp_path):
        assert detect_file_type(tmp_path / "package.json") == ("json", None)

    def test_yaml_file(self, tmp_path):
        assert detect_file_type(tmp_path / "config.yaml") == ("json", None)

    def test_yml_file(self, tmp_path):
        assert detect_file_type(tmp_path / "config.yml") == ("json", None)

    def test_toml_file(self, tmp_path):
        assert detect_file_type(tmp_path / "pyproject.toml") == ("json", None)

    def test_text_file(self, tmp_path):
        assert detect_file_type(tmp_path / "notes.txt") == ("text", None)

    def test_csv_file(self, tmp_path):
        assert detect_file_type(tmp_path / "data.csv") == ("text", None)

    def test_unknown_extension_defaults_to_text(self, tmp_path):
        assert detect_file_type(tmp_path / "data.xyz") == ("text", None)

    def test_no_extension_unknown_defaults_to_text(self, tmp_path):
        assert detect_file_type(tmp_path / "randomfile") == ("text", None)

    def test_makefile_by_name(self, tmp_path):
        assert detect_file_type(tmp_path / "Makefile") == ("code", "makefile")

    def test_dockerfile_by_name(self, tmp_path):
        assert detect_file_type(tmp_path / "Dockerfile") == ("code", "dockerfile")

    def test_gitignore_by_name(self, tmp_path):
        assert detect_file_type(tmp_path / ".gitignore") == ("text", None)

    def test_case_insensitive_extension(self, tmp_path):
        """Extensions are lowercased before lookup."""
        assert detect_file_type(tmp_path / "Main.PY") == ("code", "python")


class TestParseFile:
    """Tests for parse_file."""

    def test_parse_python(self, python_file):
        result = parse_file(python_file)
        assert result["file_type"] == "code"
        assert result["language"] == "python"
        assert "def hello" in result["text"]
        assert result["file_path"] == str(python_file)

    def test_parse_markdown(self, markdown_file):
        result = parse_file(markdown_file)
        assert result["file_type"] == "markdown"
        assert result["language"] is None
        assert "# Project Title" in result["text"]

    def test_parse_html(self, html_file):
        result = parse_file(html_file)
        assert result["file_type"] == "markup"
        assert "parsed" in result
        # parsed content should have script/style stripped
        assert "alert" not in result["parsed"]
        assert "Welcome" in result["parsed"]

    def test_parse_json(self, json_file):
        result = parse_file(json_file)
        assert result["file_type"] == "json"
        assert result["language"] is None
        assert "test-project" in result["text"]

    def test_parse_unknown_extension(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("some unknown content")
        result = parse_file(f)
        assert result["file_type"] == "text"
        assert result["text"] == "some unknown content"

    def test_parse_empty_file(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        result = parse_file(f)
        assert result["text"] == ""
        assert result["file_type"] == "code"
