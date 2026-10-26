"""`.github/scripts/uv_lock_changes.py` renders a uv.lock diff as a table.

The script runs in CI outside any package, so it is loaded by path.
"""

from __future__ import annotations

import importlib.util
import urllib.error
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# The script needs `tomllib` (3.11+); `uv run --script` selects a 3.11+
# interpreter to satisfy its `requires-python`, while the workspace still
# supports 3.10.
pytest.importorskip("tomllib")

_SCRIPT = Path(__file__).with_name("uv_lock_changes.py")
_spec = importlib.util.spec_from_file_location("uv_lock_changes", _SCRIPT)
assert _spec is not None and _spec.loader is not None
ulc: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ulc)

Fetch = Callable[[str], dict[str, Any]]
PYPI = '{ registry = "https://pypi.org/simple" }'


def lock(*packages: tuple[str, str, str]) -> str:
    return "version = 1\n\n" + "\n".join(
        f'[[package]]\nname = "{n}"\nversion = "{v}"\nsource = {s}\n'
        for n, v, s in packages
    )


def pypi(project_urls: Any) -> Fetch:
    """Stub a PyPI JSON lookup that returns `project_urls`."""

    def fetch(url: str) -> dict[str, Any]:
        return {"info": {"project_urls": project_urls}}

    return fetch


def no_network(url: str) -> dict[str, Any]:
    raise urllib.error.URLError("offline")


class TestDiffLocks:
    def test_reports_only_packages_whose_versions_differ(self) -> None:
        before = ulc.parse_lock(lock(("ruff", "0.16.9", PYPI), ("attrs", "25.1", PYPI)))
        after = ulc.parse_lock(lock(("ruff", "0.17.0", PYPI), ("attrs", "25.1", PYPI)))
        assert ulc.diff_locks(before, after) == [
            ulc.Change("ruff", ("0.16.9",), ("0.17.0",), on_pypi=True)
        ]

    def test_includes_added_and_removed_sorted_by_name(self) -> None:
        before = ulc.parse_lock(lock(("zeta", "1", PYPI)))
        after = ulc.parse_lock(lock(("alpha", "2", PYPI)))
        assert [(c.name, c.before, c.after) for c in ulc.diff_locks(before, after)] == [
            ("alpha", (), ("2",)),
            ("zeta", ("1",), ()),
        ]

    def test_groups_a_package_locked_at_several_versions(self) -> None:
        before = ulc.parse_lock(
            lock(("numpy", "2.2.6", PYPI), ("numpy", "2.3.4", PYPI))
        )
        after = ulc.parse_lock(lock(("numpy", "2.2.6", PYPI), ("numpy", "2.3.5", PYPI)))
        assert ulc.diff_locks(before, after) == [
            ulc.Change("numpy", ("2.2.6", "2.3.4"), ("2.2.6", "2.3.5"), on_pypi=True)
        ]

    def test_keeps_versions_in_lock_order(self) -> None:
        # uv writes a package's entries in version order; a string sort would
        # put 1.11.0 before 1.8.0.
        locked = ulc.parse_lock(lock(("j", "1.8.0", PYPI), ("j", "1.11.0", PYPI)))
        assert locked["j"].versions == ("1.8.0", "1.11.0")

    def test_marks_workspace_members_as_not_on_pypi(self) -> None:
        member = '{ editable = "packages/x" }'
        after = ulc.parse_lock(lock(("x", "2", member)))
        assert ulc.diff_locks({}, after)[0].on_pypi is False

    def test_links_follow_the_after_source(self) -> None:
        before = ulc.parse_lock(lock(("x", "1", PYPI)))
        after = ulc.parse_lock(lock(("x", "2", '{ editable = "packages/x" }')))
        assert ulc.diff_locks(before, after)[0].on_pypi is False

    def test_names_a_dynamic_version(self) -> None:
        # uv omits `version` for a package that declares `dynamic = ["version"]`.
        text = 'version = 1\n\n[[package]]\nname = "x"\nsource = { editable = "x" }\n'
        assert ulc.parse_lock(text)["x"].versions == ("dynamic",)


class TestReleaseLink:
    @pytest.mark.parametrize(
        "url",
        ["https://example.com/a|b", "https://example.com/a)b", "javascript:x", None],
    )
    def test_ignores_a_changelog_url_that_would_break_the_table(
        self, url: object
    ) -> None:
        assert ulc.release_link("p", "1", pypi({"Changelog": url})) == (
            "PyPI",
            "https://pypi.org/project/p/1/",
        )

    def test_prefers_a_changelog_project_url(self) -> None:
        stub = pypi(
            {
                "Source": "https://github.com/astral-sh/ruff",
                "Changelog": "https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md",
            }
        )

        def fetch(url: str) -> dict[str, Any]:
            assert url == "https://pypi.org/pypi/ruff/0.17.0/json"
            return stub(url)

        assert ulc.release_link("ruff", "0.17.0", fetch) == (
            "changelog",
            "https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md",
        )

    @pytest.mark.parametrize(
        "key", ["Release Notes", "release-notes", "History", "Changes"]
    )
    def test_recognizes_changelog_key_variants(self, key: str) -> None:
        fetch = pypi({key: "https://example.com/notes"})
        assert ulc.release_link("p", "1", fetch) == (
            "changelog",
            "https://example.com/notes",
        )

    def test_falls_back_to_the_pypi_release_page(self) -> None:
        assert ulc.release_link("attrs", "25.4.0", pypi(None)) == (
            "PyPI",
            "https://pypi.org/project/attrs/25.4.0/",
        )

    @pytest.mark.parametrize(
        "fetch", [lambda url: {}, pypi(["https://example.com/log"])]
    )
    def test_malformed_payload_falls_back_to_the_pypi_release_page(
        self, fetch: Fetch
    ) -> None:
        assert ulc.release_link("attrs", "25.4.0", fetch) == (
            "PyPI",
            "https://pypi.org/project/attrs/25.4.0/",
        )

    def test_network_failure_falls_back_to_the_pypi_release_page(self) -> None:
        assert ulc.release_link("attrs", "25.4.0", no_network) == (
            "PyPI",
            "https://pypi.org/project/attrs/25.4.0/",
        )


class TestRender:
    def test_renders_a_table_with_links_for_new_pypi_versions(self) -> None:
        rows = [
            ulc.Change("alpha", (), ("2",), on_pypi=True),
            ulc.Change("member", ("1",), ("2",), on_pypi=False),
            ulc.Change("zeta", ("1",), (), on_pypi=True),
        ]
        assert ulc.render(rows, no_network) == (
            "| Package | From | To | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| alpha | *added* | 2 | [PyPI](https://pypi.org/project/alpha/2/) |\n"
            "| member | 1 | 2 |  |\n"
            "| zeta | 1 | *removed* |  |\n"
        )

    def test_links_only_versions_new_to_the_lock(self) -> None:
        rows = [
            ulc.Change("numpy", ("2.2.6", "2.3.4"), ("2.2.6", "2.3.5"), on_pypi=True)
        ]
        assert ulc.render(rows, no_network).splitlines()[-1] == (
            "| numpy | 2.2.6, 2.3.4 | 2.2.6, 2.3.5 "
            "| [PyPI](https://pypi.org/project/numpy/2.3.5/) |"
        )

    def test_lists_a_link_shared_by_several_new_versions_once(self) -> None:
        fetch = pypi({"Changelog": "https://example.com/log"})
        rows = [ulc.Change("numpy", ("2.2.6",), ("2.4.6", "2.5.3"), on_pypi=True)]
        assert (
            ulc.render(rows, fetch)
            .splitlines()[-1]
            .endswith("| [changelog](https://example.com/log) |")
        )

    def test_links_mixed_outcomes_in_lock_order(self) -> None:
        def fetch(url: str) -> dict[str, Any]:
            if "/2.4.6/" in url:
                return pypi({"Changelog": "https://example.com/log"})(url)
            return no_network(url)

        rows = [ulc.Change("numpy", ("2.2.6",), ("2.4.6", "2.5.3"), on_pypi=True)]
        assert (
            ulc.render(rows, fetch)
            .splitlines()[-1]
            .endswith(
                "| [changelog](https://example.com/log) "
                "[PyPI](https://pypi.org/project/numpy/2.5.3/) |"
            )
        )

    def test_says_so_when_no_version_changed(self) -> None:
        assert ulc.render([], no_network) == "No package versions changed.\n"


def test_main_diffs_two_lock_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "before").write_text(lock(("ruff", "0.16.9", PYPI)))
    (tmp_path / "after").write_text(lock(("ruff", "0.17.0", PYPI)))
    ulc.main([str(tmp_path / "before"), str(tmp_path / "after")], fetch=no_network)
    assert "| ruff | 0.16.9 | 0.17.0 |" in capsys.readouterr().out
