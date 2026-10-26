#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///

"""
Render the package versions that differ between two uv.lock files.

Run by `uv-lock-refresh.yml` to write the refresh PR's table of changes:

    uv run --script .github/scripts/uv_lock_changes.py <before-lock> <after-lock>

Reads each lock's `[[package]]` entries and prints a Markdown table of every
package whose locked versions changed, sorted by name, including
packages added or removed. A package locked at several versions (uv forks the
resolution per Python version) is one row listing them all.

Each version new to the lock gets a link: the changelog or release notes named
in its PyPI `project_urls`, else its PyPI release page. A failed PyPI lookup
falls back to the release page rather than failing the run. Packages not from
PyPI (workspace members) get no link.
"""

import json
import re
import sys
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, NamedTuple

import tomllib

PYPI_INDEX = "https://pypi.org/simple"

# `project_urls` keys, reduced to lowercase letters, that name
# a changelog. Projects label it freely, so match on these substrings.
CHANGELOG_KEYS = ("changelog", "changes", "releasenotes", "history", "whatsnew", "news")

# A `project_urls` value goes into a Markdown table cell as a link target, so
# accept only an http(s) URL with nothing that ends the link or the cell.
TABLE_SAFE_URL = re.compile(r"https?://[^\s|()<>\[\]]+")

LOOKUP_TIMEOUT_SECONDS = 10
LOOKUP_CONCURRENCY = 8

Fetch = Callable[[str], dict[str, Any]]


class LockEntry(NamedTuple):
    versions: tuple[str, ...]
    on_pypi: bool


class Change(NamedTuple):
    name: str
    before: tuple[str, ...]
    after: tuple[str, ...]
    on_pypi: bool


def parse_lock(text: str) -> dict[str, LockEntry]:
    """Map each package name in a uv.lock to its locked versions and origin."""
    versions: dict[str, dict[str, None]] = {}
    on_pypi: dict[str, bool] = {}
    for pkg in tomllib.loads(text).get("package", []):
        # uv omits `version` for a package declaring `dynamic = ["version"]`.
        versions.setdefault(pkg["name"], {})[pkg.get("version", "dynamic")] = None
        on_pypi[pkg["name"]] = pkg.get("source", {}).get("registry") == PYPI_INDEX
    return {n: LockEntry(tuple(v), on_pypi[n]) for n, v in versions.items()}


def diff_locks(
    before: dict[str, LockEntry], after: dict[str, LockEntry]
) -> list[Change]:
    """List packages whose locked versions differ, sorted by name."""
    missing = LockEntry((), on_pypi=False)
    result = []
    for name in sorted(before.keys() | after.keys()):
        b, a = before.get(name, missing), after.get(name, missing)
        if b.versions != a.versions:
            result.append(Change(name, b.versions, a.versions, a.on_pypi))
    return result


def fetch_json(url: str) -> dict[str, Any]:
    """GET a URL and parse its JSON body."""
    with urllib.request.urlopen(url, timeout=LOOKUP_TIMEOUT_SECONDS) as response:
        return dict(json.load(response))


def release_link(name: str, version: str, fetch: Fetch = fetch_json) -> tuple[str, str]:
    """Return a (label, url) link to a PyPI release's changelog or release page."""
    try:
        info = fetch(f"https://pypi.org/pypi/{name}/{version}/json")["info"]
        for key, url in (info.get("project_urls") or {}).items():
            normalized = re.sub(r"[^a-z]", "", key.lower())
            is_changelog = any(k in normalized for k in CHANGELOG_KEYS)
            if is_changelog and isinstance(url, str) and TABLE_SAFE_URL.fullmatch(url):
                return "changelog", url
    except Exception:
        # Any lookup failure, malformed payloads included, falls back to the
        # release page.
        pass
    return "PyPI", f"https://pypi.org/project/{name}/{version}/"


def render(rows: Sequence[Change], fetch: Fetch = fetch_json) -> str:
    """Render changes as a Markdown table, looking up links concurrently."""
    if not rows:
        return "No package versions changed.\n"
    new_releases = [
        (r.name, v) for r in rows if r.on_pypi for v in r.after if v not in r.before
    ]
    with ThreadPoolExecutor(max_workers=LOOKUP_CONCURRENCY) as pool:
        release_links = pool.map(
            lambda nv: release_link(nv[0], nv[1], fetch), new_releases
        )
        links = dict(zip(new_releases, release_links, strict=True))
    lines = ["| Package | From | To | Notes |", "| --- | --- | --- | --- |"]
    for r in rows:
        # Several new versions often share one changelog URL; list it once.
        row_links = dict.fromkeys(
            links[r.name, v] for v in r.after if (r.name, v) in links
        )
        notes = " ".join(f"[{label}]({url})" for label, url in row_links)
        lines.append(
            f"| {r.name} | {_versions(r.before, '*added*')} "
            f"| {_versions(r.after, '*removed*')} | {notes} |"
        )
    return "\n".join(lines) + "\n"


def _versions(versions: Iterable[str], absent: str) -> str:
    return ", ".join(versions) or absent


def main(argv: Sequence[str], fetch: Fetch = fetch_json) -> None:
    """Print the change table for `before-lock after-lock`."""
    if len(argv) != 2:
        sys.exit("usage: uv_lock_changes.py <before-lock> <after-lock>")
    before, after = (parse_lock(Path(p).read_text()) for p in argv)
    sys.stdout.write(render(diff_locks(before, after), fetch))


if __name__ == "__main__":
    main(sys.argv[1:])
