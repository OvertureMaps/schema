"""Tests for module_layout: output directory layout from module paths."""

from pathlib import PurePosixPath

import pytest
from overture.schema.codegen.layout.module_layout import (
    compute_output_dir,
    compute_schema_root,
    entry_point_class,
    entry_point_module,
    is_package_module,
    module_relpath,
)


class TestComputeSchemaRoot:
    def test_multiple_paths_common_prefix(self) -> None:
        paths = [
            "overture.schema.buildings",
            "overture.schema.places",
            "overture.schema.divisions",
        ]
        assert compute_schema_root(paths) == "overture.schema"

    def test_single_path_drops_last_component(self) -> None:
        assert compute_schema_root(["overture.schema.buildings"]) == "overture.schema"

    def test_mixed_depth_paths(self) -> None:
        paths = [
            "overture.schema.buildings",
            "overture.schema.common.names.primary_name",
        ]
        assert compute_schema_root(paths) == "overture.schema"

    def test_divergent_namespaces(self) -> None:
        paths = ["overture.schema.buildings", "acme.transit"]
        assert compute_schema_root(paths) == ""

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_schema_root([])

    def test_single_component_path(self) -> None:
        assert compute_schema_root(["buildings"]) == ""

    def test_identical_paths_deduplicated(self) -> None:
        paths = ["overture.schema.buildings", "overture.schema.buildings"]
        assert compute_schema_root(paths) == "overture.schema"


class TestEntryPointModule:
    def test_extracts_module(self) -> None:
        assert entry_point_module("overture.schema.buildings:Building") == (
            "overture.schema.buildings"
        )

    def test_missing_colon_raises(self) -> None:
        with pytest.raises(ValueError):
            entry_point_module("no_colon")

    def test_multiple_colons_splits_on_first(self) -> None:
        assert entry_point_module("mod:A:B") == "mod"


class TestEntryPointClass:
    def test_extracts_class(self) -> None:
        assert entry_point_class("overture.schema.buildings:Building") == "Building"

    def test_missing_colon_raises(self) -> None:
        with pytest.raises(ValueError):
            entry_point_class("no_colon")

    def test_colon_at_end_returns_empty(self) -> None:
        assert entry_point_class("mod:") == ""

    def test_multiple_colons_splits_on_first(self) -> None:
        assert entry_point_class("mod:A:B") == "A:B"


class TestModuleRelpath:
    def test_strips_root_prefix(self) -> None:
        assert (
            module_relpath("overture.schema.buildings", "overture.schema")
            == "buildings"
        )

    def test_deep_path(self) -> None:
        assert (
            module_relpath(
                "overture.schema.common.names.primary_name", "overture.schema"
            )
            == "common.names.primary_name"
        )

    def test_module_equals_root(self) -> None:
        assert module_relpath("overture.schema", "overture.schema") == ""

    def test_empty_root(self) -> None:
        assert module_relpath("buildings", "") == "buildings"

    def test_nonmatching_raises(self) -> None:
        with pytest.raises(ValueError):
            module_relpath("acme.transit", "overture.schema")


def _make_registry(*entries: tuple[str, bool]) -> dict[str, object]:
    """Build a synthetic module registry.

    Each entry is (module_path, is_package). Packages get __path__;
    file modules do not.
    """
    registry: dict[str, object] = {}
    for mod_path, is_pkg in entries:
        if is_pkg:
            registry[mod_path] = type("pkg", (), {"__path__": ["/fake"]})()
        else:
            registry[mod_path] = type("mod", (), {})()
    return registry


class TestIsPackageModule:
    def test_package_has_path(self) -> None:
        registry = _make_registry(("my.package", True))
        assert is_package_module("my.package", registry) is True

    def test_file_module_no_path(self) -> None:
        registry = _make_registry(("my.module", False))
        assert is_package_module("my.module", registry) is False

    def test_missing_module_raises(self) -> None:
        with pytest.raises(ValueError):
            is_package_module("nonexistent", {})


class TestComputeOutputDir:
    def test_package_keeps_all_parts(self) -> None:
        reg = _make_registry(("overture.schema.buildings", True))
        result = compute_output_dir("overture.schema.buildings", "overture.schema", reg)
        assert result == PurePosixPath("buildings")

    def test_file_module_drops_last(self) -> None:
        reg = _make_registry(("overture.schema.common.names.primary_name", False))
        result = compute_output_dir(
            "overture.schema.common.names.primary_name", "overture.schema", reg
        )
        assert result == PurePosixPath("common/names")

    def test_deep_package(self) -> None:
        reg = _make_registry(("overture.schema.common.names", True))
        result = compute_output_dir(
            "overture.schema.common.names", "overture.schema", reg
        )
        assert result == PurePosixPath("common/names")

    def test_file_module_in_theme(self) -> None:
        reg = _make_registry(("overture.schema.buildings.enums", False))
        result = compute_output_dir(
            "overture.schema.buildings.enums", "overture.schema", reg
        )
        assert result == PurePosixPath("buildings")

    def test_file_module_deep(self) -> None:
        reg = _make_registry(("overture.schema.divisions.division.models", False))
        result = compute_output_dir(
            "overture.schema.divisions.division.models", "overture.schema", reg
        )
        assert result == PurePosixPath("divisions/division")

    def test_root_module_returns_dot(self) -> None:
        reg = _make_registry(("overture.schema", True))
        result = compute_output_dir("overture.schema", "overture.schema", reg)
        assert result == PurePosixPath(".")

    def test_file_module_one_level_returns_dot(self) -> None:
        reg = _make_registry(("overture.schema.types", False))
        result = compute_output_dir("overture.schema.types", "overture.schema", reg)
        assert result == PurePosixPath(".")
