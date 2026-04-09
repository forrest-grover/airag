"""Shared fixtures for airag tests."""

import pytest

SAMPLE_PYTHON = '''\
import os

def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

class Greeter:
    """A greeter class."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def greet(self, name: str) -> str:
        return f"{self.prefix} {name}"
'''

SAMPLE_MARKDOWN = """\
# Project Title

This is the introduction.

## Installation

Run `pip install foo` to install.

### Prerequisites

You need Python 3.11+.

## Usage

```python
import foo
foo.run()
```

## License

MIT License.
"""

SAMPLE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<h1>Welcome</h1>
<p>This is a test paragraph with some content.</p>
<script>alert("ignore me");</script>
<style>.hidden { display: none; }</style>
<div>
  <p>Nested paragraph content here.</p>
</div>
</body>
</html>
"""

SAMPLE_JSON = """\
{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "foo": "^1.0",
    "bar": "^2.0"
  },
  "scripts": {
    "build": "make build",
    "test": "pytest"
  }
}
"""

SAMPLE_YAML = """\
name: test-project
version: 1.0.0
dependencies:
  foo: "^1.0"
  bar: "^2.0"
scripts:
  build: make build
  test: pytest
"""


@pytest.fixture
def sample_python():
    return SAMPLE_PYTHON


@pytest.fixture
def sample_markdown():
    return SAMPLE_MARKDOWN


@pytest.fixture
def sample_html():
    return SAMPLE_HTML


@pytest.fixture
def sample_json():
    return SAMPLE_JSON


@pytest.fixture
def sample_yaml():
    return SAMPLE_YAML


@pytest.fixture
def python_file(tmp_path, sample_python):
    f = tmp_path / "example.py"
    f.write_text(sample_python)
    return f


@pytest.fixture
def markdown_file(tmp_path, sample_markdown):
    f = tmp_path / "README.md"
    f.write_text(sample_markdown)
    return f


@pytest.fixture
def html_file(tmp_path, sample_html):
    f = tmp_path / "page.html"
    f.write_text(sample_html)
    return f


@pytest.fixture
def json_file(tmp_path, sample_json):
    f = tmp_path / "package.json"
    f.write_text(sample_json)
    return f


@pytest.fixture
def yaml_file(tmp_path, sample_yaml):
    f = tmp_path / "config.yaml"
    f.write_text(sample_yaml)
    return f
