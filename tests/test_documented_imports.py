"""Every `overture.*` import written in repo Markdown must resolve.

Documentation drifts silently: a module moves, a helper is renamed, and the
README keeps confidently describing the old surface. This parses every fenced
Python block in every tracked Markdown file -- including blocks indented inside
a list item -- and imports each `overture.*` statement it finds.

The subject is the repo's Markdown rather than any one package, so this lives
outside `packages/`. It reaches across the whole workspace -- a README may cite
`overture.schema.codegen`, which no single distribution depends on.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import re
import subprocess
import textwrap
from enum import Enum
from pathlib import Path

import pytest

# A fenced ```python block, capturing its body. The indent group matches a
# block nested in a list item; the body is dedented before parsing, since an
# `IndentationError` is a `SyntaxError` and would file the block under
# "expected unparseable" rather than reporting it.
_PYTHON_BLOCK = re.compile(
    r"^(?P<indent> *)```python[^\n]*\n(?P<body>.*?)^(?P=indent)```",
    re.MULTILINE | re.DOTALL,
)

# Blocks that are deliberately not valid Python: illustrations whose `...`
# placeholders stand in for elided content. Pinned by identity, not count -- a
# bare total stays put when one block breaks as another is fixed. The identity
# is a digest of the block body, so reordering a document does not trip it but
# editing one of these blocks does.
_EXPECTED_UNPARSEABLE = {
    "PYDANTIC_GUIDE.md:43488ef4",
}

# An import statement, matched textually -- used to police the excuse list,
# where by definition `ast` cannot be applied.
_OVERTURE_IMPORT = re.compile(r"^\s*(?:from|import)\s+overture\b", re.MULTILINE)

# Golden files are generated fixtures, not documentation.
_EXCLUDED = "tests/golden/"


def _repo_root() -> Path:
    """Locate the checkout root, or skip the module when there isn't one."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists():
            return candidate
    pytest.skip("not running from a git checkout", allow_module_level=True)


def _markdown_files() -> list[Path]:
    root = _ROOT
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z", "*.md"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover
        pytest.skip(f"cannot list tracked files: {exc}", allow_module_level=True)
    return [root / n for n in listed.split("\0") if n and _EXCLUDED not in n]


def python_blocks(text: str) -> list[str]:
    """Yield the dedented body of every fenced Python block in `text`.

    Handles a block indented inside a list item. The dedent is load-bearing:
    without it `ast.parse` raises `IndentationError`, a `SyntaxError`, and the
    block would be filed as "expected unparseable" rather than reported.
    """
    return [textwrap.dedent(match["body"]) for match in _PYTHON_BLOCK.finditer(text)]


def _documented_enum_references(
    paths: list[Path],
) -> list[tuple[Path, str, str, str]]:
    """Collect `(file, module, enum, member)` quads across the corpus."""
    found: list[tuple[Path, str, str, str]] = []
    for path in paths:
        for body in python_blocks(path.read_text(encoding="utf-8")):
            try:
                refs = enum_references(body)
            except SyntaxError:
                continue
            found += [(path, module, name, member) for module, name, member in refs]
    return found


def parse_imports(source: str) -> list[tuple[str, str | None]]:
    """Extract `overture.*` imports from one block of Python source.

    Returns `(module, attribute)` pairs; `attribute` is None for a plain
    `import overture.x`. Raises `SyntaxError` if the block is not valid Python.
    """
    found: list[tuple[str, str | None]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            # A relative import (`from . import x`) has no absolute module.
            if node.level or not node.module or not _is_overture(node.module):
                continue
            found += [
                (node.module, alias.name) for alias in node.names if alias.name != "*"
            ]
        elif isinstance(node, ast.Import):
            found += [
                (alias.name, None) for alias in node.names if _is_overture(alias.name)
            ]
    return found


def _is_overture(module: str) -> bool:
    return module == "overture" or module.startswith("overture.")


def enum_references(source: str) -> list[tuple[str, str, str]]:
    """Find `Enum.MEMBER` uses of enums imported in the same block.

    Returns `(module, enum_name, member)`. Restricted to enums on purpose:
    their members really are class attributes, whereas a Pydantic model's
    fields are not, so `Place.addresses` would read as missing.
    """
    tree = ast.parse(source)
    imported = {
        alias.asname or alias.name: node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and not node.level
        and _is_overture(node.module)
        for alias in node.names
    }
    return [
        (imported[node.value.id], node.value.id, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in imported
        and node.attr.isupper()  # a member, not a method
    ]


def _documented_imports(
    paths: list[Path],
) -> tuple[list[tuple[Path, str, str | None]], dict[str, str]]:
    """Collect `(file, module, attribute)` triples, and identify unparseable blocks."""
    found: list[tuple[Path, str, str | None]] = []
    unparseable: dict[str, str] = {}
    for path in paths:
        for body in python_blocks(path.read_text(encoding="utf-8")):
            try:
                imports = parse_imports(body)
            except SyntaxError:
                digest = hashlib.sha256(body.encode()).hexdigest()[:8]
                unparseable[f"{path.relative_to(_ROOT)}:{digest}"] = body
                continue
            found += [(path, module, attr) for module, attr in imports]
    return found, unparseable


_ROOT = _repo_root()
_MARKDOWN = _markdown_files()
_DOCUMENTED, _UNPARSEABLE = _documented_imports(_MARKDOWN)
_ENUM_REFERENCES = _documented_enum_references(_MARKDOWN)


class TestBlocks:
    """`python_blocks` against inline fixtures.

    Same argument as `TestParser` below, one layer up: a fence form the
    matcher misses yields no block, and a sweep that collects less still
    passes. The corpus cannot pin this.
    """

    def test_flush_block(self) -> None:
        text = "text\n\n```python\nx = 1\n```\n\nmore\n"
        assert python_blocks(text) == ["x = 1\n"]

    def test_list_item_block(self) -> None:
        """A block indented under a list item, dedented to parse."""
        text = "1. Example:\n\n   ```python\n   x = 1\n   ```\n"
        assert python_blocks(text) == ["x = 1\n"]

    def test_deeply_indented_block(self) -> None:
        text = "- a\n    - b\n\n    ```python\n    x = 1\n    ```\n"
        assert python_blocks(text) == ["x = 1\n"]

    def test_indented_block_parses_only_after_dedent(self) -> None:
        """Without the dedent this is an IndentationError, i.e. excused."""
        text = (
            "- item\n\n  ```python\n  from overture.schema.places import Place\n  ```\n"
        )
        (body,) = python_blocks(text)
        assert parse_imports(body) == [("overture.schema.places", "Place")]

    def test_relative_indent_inside_a_block_is_preserved(self) -> None:
        text = "- item\n\n  ```python\n  def f():\n      return 1\n  ```\n"
        assert python_blocks(text) == ["def f():\n    return 1\n"]

    def test_non_python_fences_are_ignored(self) -> None:
        text = "```toml\nx = 1\n```\n\n```\nplain\n```\n"
        assert python_blocks(text) == []

    def test_several_blocks(self) -> None:
        text = "```python\na = 1\n```\n\ntext\n\n```python\nb = 2\n```\n"
        assert python_blocks(text) == ["a = 1\n", "b = 2\n"]


class TestOvertureImportMatcher:
    """`_OVERTURE_IMPORT` against fixtures.

    It polices the excuse list, where `ast` cannot be applied by definition.
    No excused block imports `overture` today, so the corpus never exercises
    it -- the matcher would go blind without anyone noticing.
    """

    def test_matches_from_import(self) -> None:
        assert _OVERTURE_IMPORT.search("x = 1\nfrom overture.schema import y\n")

    def test_matches_plain_import(self) -> None:
        assert _OVERTURE_IMPORT.search("  import overture.schema.places\n")

    def test_ignores_other_packages(self) -> None:
        assert not _OVERTURE_IMPORT.search("import json\nfrom pydantic import X\n")

    def test_ignores_a_longer_name(self) -> None:
        assert not _OVERTURE_IMPORT.search("import overtures\n")

    def test_ignores_a_mention_in_prose(self) -> None:
        assert not _OVERTURE_IMPORT.search("# import overture is what you'd write\n")


class TestParser:
    """`parse_imports` against inline fixtures.

    The corpus cannot test the parser: any form it fails to handle simply
    yields nothing, and a sweep that collects less still passes.
    """

    def test_single_line(self) -> None:
        assert parse_imports("from overture.schema.buildings import Building") == [
            ("overture.schema.buildings", "Building")
        ]

    def test_wrapped(self) -> None:
        """The form `ruff format` produces once the names outgrow a line."""
        source = (
            "from overture.schema.system.numeric import (\n"
            "    int8,  # signed\n"
            "    float64,\n"
            ")\n"
        )
        assert parse_imports(source) == [
            ("overture.schema.system.numeric", "int8"),
            ("overture.schema.system.numeric", "float64"),
        ]

    def test_alias(self) -> None:
        assert parse_imports("from overture.schema.places import Place as P") == [
            ("overture.schema.places", "Place")
        ]

    def test_plain_import_with_alias(self) -> None:
        assert parse_imports("import overture.schema.buildings as b") == [
            ("overture.schema.buildings", None)
        ]

    def test_star_and_relative_are_skipped(self) -> None:
        assert parse_imports("from overture.schema.buildings import *") == []
        assert parse_imports("from . import buildings") == []

    def test_non_overture_is_skipped(self) -> None:
        assert parse_imports("import json\nfrom pydantic import BaseModel") == []

    def test_indented_import(self) -> None:
        source = "def f():\n    from overture.schema.places import Place\n"
        assert parse_imports(source) == [("overture.schema.places", "Place")]

    def test_invalid_source_raises(self) -> None:
        with pytest.raises(SyntaxError):
            parse_imports('{"a": 1, ...}\nthis is not python')


def test_corpus_is_non_empty() -> None:
    """Guard against a silently empty sweep reporting success.

    The thresholds only have to be low enough to survive ordinary doc churn
    and high enough that an empty or near-empty parse fails loudly.
    """
    assert len(_MARKDOWN) > 10
    assert len(_DOCUMENTED) > 20


def test_unparseable_blocks_are_the_expected_ones() -> None:
    """A block that stops parsing drops out of the sweep silently."""
    assert set(_UNPARSEABLE) == _EXPECTED_UNPARSEABLE


def test_no_excused_block_hides_an_import() -> None:
    """An excused block may illustrate, but may not cite the API.

    A content-addressed waiver is durable, so a block that both fails to
    parse and imports `overture.*` would be exempt from the sweep forever --
    the one outcome this module exists to prevent. Making the block parse is
    always available; every case so far took a one-token edit.
    """
    for name, body in _UNPARSEABLE.items():
        assert not _OVERTURE_IMPORT.search(body), (
            f"{name} is excused from parsing but imports overture.*; "
            "make the block parse instead of excusing it"
        )


@pytest.mark.parametrize(
    ("path", "module", "enum_name", "member"),
    _ENUM_REFERENCES,
    ids=[
        f"{path.relative_to(_ROOT)}:{name}.{member}"
        for path, _, name, member in _ENUM_REFERENCES
    ],
)
def test_documented_enum_member_exists(
    path: Path, module: str, enum_name: str, member: str
) -> None:
    """An enum member named in the docs exists on the enum.

    The import sweep cannot see this: `from ... import Relationship`
    resolves whether or not `Relationship.CONNECTS_TO` does.
    """
    enum_class = getattr(importlib.import_module(module), enum_name)
    if not (isinstance(enum_class, type) and issubclass(enum_class, Enum)):
        return
    names = [m.name for m in enum_class]
    assert member in names, (
        f"{path}: `{enum_name}` has no member `{member}`; it has {names}"
    )


@pytest.mark.parametrize(
    ("path", "module", "attribute"),
    _DOCUMENTED,
    ids=[
        f"{path.relative_to(_ROOT)}:{module}" + (f".{attr}" if attr else "")
        for path, module, attr in _DOCUMENTED
    ],
)
def test_documented_import_resolves(
    path: Path, module: str, attribute: str | None
) -> None:
    """An import written in the docs imports cleanly."""
    imported = importlib.import_module(module)
    if attribute is None or hasattr(imported, attribute):
        return
    # `from pkg import submodule` binds only once the submodule is imported.
    try:
        importlib.import_module(f"{module}.{attribute}")
    except ImportError as exc:
        pytest.fail(f"{path}: `{module}` has no attribute `{attribute}` ({exc})")
