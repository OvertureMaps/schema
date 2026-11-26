#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py>=4.0.0"]
# ///

"""
Join each hard-wrapped paragraph of a package's changelog fragments onto one line.

Run by `make changelog` on each package's `changelog.d/` before towncrier folds
the fragments into `CHANGELOG.md`:

    uv run --script scripts/unwrap_fragments.py packages/<package>/changelog.d

`release-trigger` copies each released section of `CHANGELOG.md` into the
GitHub Release body, where every newline inside a paragraph renders as a line
break. Without this step a fragment wrapped at 90 columns breaks mid-sentence in
the release notes and one written on a single line does not.

Only paragraphs change, located by parsing the fragment as Markdown: a
paragraph's lines are joined with single spaces, including a paragraph inside a
list item. Everything else stays byte-identical: fenced and indented code,
tables, headings, blockquotes, and a line ending in a hard break (a trailing
backslash or two spaces). Every `*.md` in the directory is rewritten in place
except `README.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from markdown_it import MarkdownIt

_PARSER = MarkdownIt("commonmark").enable("table")


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Return the `[start, end)` source line range of each multi-line paragraph.

    Paragraphs inside a blockquote are left out: their lines carry `>` markers
    that a join would carry into the middle of the line.
    """
    spans = []
    quote_depth = 0
    for token in _PARSER.parse(text):
        if token.type == "blockquote_open":
            quote_depth += 1
        elif token.type == "blockquote_close":
            quote_depth -= 1
        elif token.type == "paragraph_open" and quote_depth == 0 and token.map:
            start, end = token.map
            if end - start > 1:
                spans.append((start, end))
    return spans


def _ends_in_hard_break(line: str) -> bool:
    return line.endswith(("\\", "  "))


def unwrap(text: str) -> str:
    """Join the lines of each Markdown paragraph in `text`.

    Parameters
    ----------
    text : str
        Markdown source.

    Returns
    -------
    str
        `text` with each paragraph on one line, or on one line per hard break.
    """
    lines = text.split("\n")
    for start, end in reversed(_paragraph_spans(text)):
        joined = [lines[start]]
        for line in lines[start + 1 : end]:
            if _ends_in_hard_break(joined[-1]):
                joined.append(line)
            else:
                joined[-1] = f"{joined[-1].rstrip()} {line.strip()}"
        lines[start:end] = joined
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    """Unwrap every fragment in each directory named in `argv`.

    Parameters
    ----------
    argv : list[str]
        `changelog.d` directories.
    """
    for directory in argv:
        for fragment in sorted(Path(directory).glob("*.md")):
            if fragment.name == "README.md":
                continue
            text = fragment.read_text()
            unwrapped = unwrap(text)
            if unwrapped != text:
                fragment.write_text(unwrapped)


if __name__ == "__main__":
    main(sys.argv[1:])
