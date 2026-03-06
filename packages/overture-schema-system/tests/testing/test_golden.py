"""Tests for the golden file comparison helpers."""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from overture.schema.system.testing import (
    assert_golden,
    assert_json_schema_golden,
)


class _Minimal(BaseModel):
    name: str


class TestAssertGolden:
    """Tests for assert_golden."""

    def test_passes_when_content_matches(self, tmp_path: Path) -> None:
        golden = tmp_path / "test.txt"
        golden.write_text("hello")
        assert_golden("hello", golden, update=False)

    def test_fails_with_diff_on_mismatch(self, tmp_path: Path) -> None:
        golden = tmp_path / "test.txt"
        golden.write_text("hello")
        with pytest.raises(AssertionError, match="Golden file mismatch"):
            assert_golden("goodbye", golden, update=False)

    def test_diff_shows_both_sides(self, tmp_path: Path) -> None:
        golden = tmp_path / "test.txt"
        golden.write_text("line1\nline2")
        with pytest.raises(AssertionError, match=r"(?s)-line2.*\+line3"):
            assert_golden("line1\nline3", golden, update=False)

    def test_update_writes_file(self, tmp_path: Path) -> None:
        golden = tmp_path / "test.txt"
        assert_golden("new content", golden, update=True)
        assert golden.read_text() == "new content"

    def test_update_overwrites_existing(self, tmp_path: Path) -> None:
        golden = tmp_path / "test.txt"
        golden.write_text("old")
        assert_golden("new", golden, update=True)
        assert golden.read_text() == "new"

    def test_missing_file_without_update_fails(self, tmp_path: Path) -> None:
        golden = tmp_path / "nonexistent.txt"
        with pytest.raises(AssertionError, match="make update-baselines"):
            assert_golden("anything", golden, update=False)


class TestAssertJsonSchemaGolden:
    """Tests for assert_json_schema_golden."""

    def test_passes_when_schema_matches(self, tmp_path: Path) -> None:
        golden = tmp_path / "minimal.json"
        assert_json_schema_golden(_Minimal, golden, update=True)
        assert_json_schema_golden(_Minimal, golden, update=False)

    def test_update_writes_schema(self, tmp_path: Path) -> None:
        golden = tmp_path / "minimal.json"
        assert_json_schema_golden(_Minimal, golden, update=True)
        written = json.loads(golden.read_text())
        assert written["title"] == "_Minimal"
        assert "name" in written["properties"]

    def test_fails_on_schema_mismatch(self, tmp_path: Path) -> None:
        golden = tmp_path / "minimal.json"
        golden.write_text('{"wrong": "schema"}')
        with pytest.raises(AssertionError, match="Golden file mismatch"):
            assert_json_schema_golden(_Minimal, golden, update=False)
