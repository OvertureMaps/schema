"""`scripts/unwrap_fragments.py` joins each Markdown paragraph onto one line.

The script runs outside any package, so it is loaded by path.
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "unwrap_fragments.py"
_spec = importlib.util.spec_from_file_location("unwrap_fragments", _SCRIPT)
assert _spec is not None and _spec.loader is not None
uf: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uf)


def _md(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            "Fixed the thing\nthat was broken.\n",
            "Fixed the thing that was broken.\n",
            id="paragraph",
        ),
        pytest.param(
            "Fixed the thing that was broken.\n",
            "Fixed the thing that was broken.\n",
            id="already-one-line",
        ),
        pytest.param(
            "First paragraph,\nwrapped.\n\nSecond paragraph,\nwrapped.\n",
            "First paragraph, wrapped.\n\nSecond paragraph, wrapped.\n",
            id="two-paragraphs",
        ),
        pytest.param(
            _md("""
                It has two parts:

                - the first part,
                  wrapped
                - the second part
                  1. nested,
                     wrapped
            """),
            _md("""
                It has two parts:

                - the first part, wrapped
                - the second part
                  1. nested, wrapped
            """),
            id="lists",
        ),
        pytest.param(
            "A line ending in a hard break\\\nstays broken.\n",
            "A line ending in a hard break\\\nstays broken.\n",
            id="backslash-hard-break",
        ),
    ],
)
def test_unwrap(source: str, expected: str) -> None:
    assert uf.unwrap(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            _md("""
                ```python
                x = (1,
                     2)
                ```
            """),
            id="fenced-code",
        ),
        pytest.param(
            _md("""
                | Column | Other |
                |---|---|
                | a | b |
            """),
            id="table",
        ),
        pytest.param(
            "> A quoted\n> paragraph.\n",
            id="blockquote",
        ),
        pytest.param(
            "    indented\n    code\n",
            id="indented-code",
        ),
    ],
)
def test_blocks_other_than_paragraphs_are_unchanged(source: str) -> None:
    assert uf.unwrap(source) == source


def test_main_rewrites_fragments_and_skips_readme(tmp_path: Path) -> None:
    (tmp_path / "1.bugfix.md").write_text("Fixed a\nthing.\n")
    (tmp_path / "README.md").write_text("A wrapped\nREADME.\n")
    uf.main([str(tmp_path)])
    assert (tmp_path / "1.bugfix.md").read_text() == "Fixed a thing.\n"
    assert (tmp_path / "README.md").read_text() == "A wrapped\nREADME.\n"
