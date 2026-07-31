"""Tests for CLI helper functions (load_input, perform_validation)."""

import io
import json
from pathlib import Path
from typing import Literal, cast

import pytest
import yaml
from click.exceptions import UsageError
from conftest import build_feature
from overture.schema.cli.commands import (
    _best_fit_model,
    _revalidate_undiscriminatable_items,
    load_input,
    perform_validation,
    resolve_types,
)
from overture.schema.cli.type_analysis import get_item_index
from overture.schema.cli.types import ValidationErrorDict
from overture.schema.system.discovery import TagSelector
from pydantic import BaseModel, ValidationError


class TestLoadInput:
    """Tests for load_input function.

    Note: Happy-path file and stdin loading are covered by integration tests
    in test_cli_commands.py. These tests focus on error cases and edge cases.
    """

    def test_load_input_file_not_found(self) -> None:
        """Test that load_input raises UsageError when file doesn't exist."""

        with pytest.raises(UsageError) as exc_info:
            load_input(Path("/nonexistent/path/to/file.yaml"))

        assert "is not a file" in str(exc_info.value)

    def test_load_input_path_is_directory(
        self, cli_runner: pytest.FixtureRequest
    ) -> None:
        """Test that load_input raises UsageError when path is a directory.

        Note: cli_runner provides isolated filesystem for test file creation.
        """

        # Create a directory
        Path("testdir").mkdir()

        with pytest.raises(UsageError) as exc_info:
            load_input(Path("testdir"))

        assert "is not a file" in str(exc_info.value)

    def test_load_input_invalid_yaml(self, cli_runner: pytest.FixtureRequest) -> None:
        """Test that load_input raises YAMLError for invalid YAML.

        Note: cli_runner provides isolated filesystem for test file creation.
        """
        invalid_yaml = "test.yaml"
        with open(invalid_yaml, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            load_input(Path(invalid_yaml))

    def test_load_input_handles_json(self, cli_runner: pytest.FixtureRequest) -> None:
        """Test that load_input can parse JSON files.

        Note: cli_runner provides isolated filesystem for test file creation.
        """
        json_file = "test.json"
        feature = build_feature()
        with open(json_file, "w") as f:
            f.write(json.dumps(feature))

        data, source_name = load_input(Path(json_file))

        assert isinstance(data, dict)
        assert data["id"] == "test"
        assert source_name == json_file

    def test_load_input_handles_list(self, cli_runner: pytest.FixtureRequest) -> None:
        """Test that load_input can parse YAML lists.

        Note: cli_runner provides isolated filesystem for test file creation.
        """
        list_file = "list.yaml"
        feature1 = build_feature(id="test1")
        feature2 = build_feature(id="test2")
        with open(list_file, "w") as f:
            f.write(yaml.dump([feature1, feature2]))

        data, source_name = load_input(Path(list_file))

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "test1"

    @pytest.mark.parametrize(
        "extension",
        [".txt", ".csv", ".xml", ".data", ""],
    )
    def test_load_input_warns_unexpected_extension(
        self,
        cli_runner: pytest.FixtureRequest,
        capsys: pytest.CaptureFixture,
        extension: str,
    ) -> None:
        """Test that load_input warns about unexpected file extensions.

        Note: cli_runner provides isolated filesystem for test file creation.
        """
        filename = f"data{extension}"
        feature = build_feature()
        with open(filename, "w") as f:
            f.write(json.dumps(feature))

        load_input(Path(filename))

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "unexpected extension" in captured.err
        assert filename in captured.err

    @pytest.mark.parametrize(
        "extension",
        [".json", ".yaml", ".yml", ".geojson"],
    )
    def test_load_input_no_warning_expected_extension(
        self,
        cli_runner: pytest.FixtureRequest,
        capsys: pytest.CaptureFixture,
        extension: str,
    ) -> None:
        """Test that load_input does not warn for expected file extensions.

        Note: cli_runner provides isolated filesystem for test file creation.
        """
        filename = f"data{extension}"
        feature = build_feature()
        with open(filename, "w") as f:
            f.write(json.dumps(feature))

        load_input(Path(filename))

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_load_input_binary_file(self, cli_runner: pytest.FixtureRequest) -> None:
        """Test graceful failure on binary files.

        Note: cli_runner provides isolated filesystem for test file creation.
        """
        binary_file = "binary.dat"
        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\xff\xfe")

        with pytest.raises((yaml.YAMLError, UnicodeDecodeError)):
            load_input(Path(binary_file))

    def test_load_input_unicode_filenames(
        self, cli_runner: pytest.FixtureRequest
    ) -> None:
        """Test files with unicode names.

        Note: cli_runner provides isolated filesystem for test file creation.
        """
        unicode_filename = "données_測試_🏢.json"
        feature = build_feature()
        with open(unicode_filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(feature))

        data, source_name = load_input(Path(unicode_filename))

        assert isinstance(data, dict)
        assert data["id"] == "test"
        assert source_name == unicode_filename

    def test_load_input_jsonl_from_stdin(
        self, cli_runner: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that load_input handles newline-delimited JSON (JSONL) from stdin.

        JSONL format is commonly used for streaming GeoJSON features where each line
        is a complete JSON object/feature.
        """
        feature1 = build_feature(id="test1")
        feature2 = build_feature(id="test2")
        jsonl_input = f"{json.dumps(feature1)}\n{json.dumps(feature2)}\n"

        # Mock stdin with JSONL content
        monkeypatch.setattr("sys.stdin", io.StringIO(jsonl_input))

        data, source_name = load_input(Path("-"))

        assert source_name == "<stdin>"
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "test1"
        assert data[1]["id"] == "test2"


class TestPerformValidation:
    """Tests for perform_validation function.

    Note: Happy-path validation (single features, lists, FeatureCollections, flat format)
    is covered by integration tests in test_cli_commands.py. These tests focus on edge
    cases and validation logic specific to the function.
    """

    def test_perform_validation_raises_for_invalid_single_feature(self) -> None:
        """Test that perform_validation raises ValidationError for single invalid feature."""
        data = build_feature(id=None)  # Missing required 'id'
        model_type = resolve_types(
            TagSelector(include_any=("overture:theme=buildings",))
        )

        with pytest.raises(ValidationError) as exc_info:
            perform_validation(data, model_type)

        errors = exc_info.value.errors()
        assert any("id" in error.get("loc", ()) for error in errors)

    def test_perform_validation_raises_for_invalid_list_item(self) -> None:
        """Test that perform_validation raises ValidationError for invalid list item."""
        feature1 = build_feature(id="test1")
        feature2 = build_feature(
            id=None, coordinates=[[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
        )
        data = [feature1, feature2]
        model_type = resolve_types(
            TagSelector(include_any=("overture:theme=buildings",))
        )

        with pytest.raises(ValidationError) as exc_info:
            perform_validation(data, model_type)

        errors = exc_info.value.errors()
        # Check that error location includes list index 1
        assert any(1 in error.get("loc", ()) for error in errors)

    def test_perform_validation_empty_list(self) -> None:
        """Test validating an empty list (edge case)."""
        data: list[dict[str, object]] = []
        model_type = resolve_types(
            TagSelector(include_any=("overture:theme=buildings",))
        )

        # Should not raise
        perform_validation(data, model_type)

    def test_perform_validation_empty_feature_collection(self) -> None:
        """Test validating an empty FeatureCollection (edge case)."""
        data = {"type": "FeatureCollection", "features": []}
        model_type = resolve_types(
            TagSelector(include_any=("overture:theme=buildings",))
        )

        # Should not raise
        perform_validation(data, model_type)

    def test_perform_validation_with_different_themes(self) -> None:
        """Test validating features from different themes."""
        data = build_feature(theme="buildings", type="building")

        # Should work with buildings theme
        buildings_type = resolve_types(
            TagSelector(include_any=("overture:theme=buildings",))
        )
        perform_validation(data, buildings_type)

        # Should fail with wrong theme
        places_type = resolve_types(TagSelector(include_any=("overture:theme=places",)))
        with pytest.raises(ValidationError):
            perform_validation(data, places_type)


class _Building(BaseModel):
    type: Literal["building"]
    id: str


class _Place(BaseModel):
    type: Literal["place"]
    id: str
    name: str


class _Sources(BaseModel):
    """A plain, non-discriminated model (no literal `type` field)."""

    datasets: list[str]


class TestRevalidateUndiscriminatableItems:
    """Tests for the best-fit re-validation of undiscriminatable list items.

    Covers an all-discriminated union (a typeless item yields only
    `union_tag_not_found` and must be re-validated to surface field errors) and
    a union that includes a plain, non-discriminated member (the typeless item
    already has concrete field errors, so the helper must be a no-op).
    """

    def test_all_discriminated_union_substitutes_best_fit_field_errors(
        self,
    ) -> None:
        """All-discriminated union: typeless item (only union_tag_not_found) -> field errors.

        With an all-discriminated union, a typeless item produces only
        `union_tag_not_found`. The helper must re-validate it against the
        candidates, pick the best fit (fewest errors -> `_Building`, which
        only needs `type`, over `_Place` which needs `type` and `name`),
        and re-home concrete field errors under the item index.
        """
        errors = cast(
            list[ValidationErrorDict],
            [
                {
                    "loc": (0, "tagged-union[type]"),
                    "msg": "Unable to extract tag",
                    "type": "union_tag_not_found",
                },
            ],
        )
        typeless_item = {"id": "x"}  # missing the 'type' discriminator

        augmented, best_fit_types = _revalidate_undiscriminatable_items(
            errors, [typeless_item], (_Building, _Place)
        )

        # Best fit is the fewest-error candidate.
        assert best_fit_types == {0: _Building}

        item0 = [e for e in augmented if get_item_index(e["loc"]) == 0]
        assert item0, "item 0 should still have errors"
        # The opaque tag-not-found noise is gone; concrete field errors remain.
        assert all(e["type"] != "union_tag_not_found" for e in item0)
        assert any(e["type"] == "missing" for e in item0)
        # Errors are re-homed under the item index.
        assert all(e["loc"][0] == 0 for e in item0)

    def test_noop_when_concrete_errors_coexist_with_tag_not_found(self) -> None:
        """A plain member yields concrete errors, so the helper is a no-op.

        When the union includes a plain (non-discriminated) member, a typeless
        item also matches that member and produces concrete `missing` errors
        alongside the discriminated branch's `union_tag_not_found`. Because the
        item already has a concrete error, the helper must leave the errors
        untouched and infer no best-fit type.
        """
        errors = cast(
            list[ValidationErrorDict],
            [
                {
                    "loc": (0, "tagged-union[type]"),
                    "msg": "Unable to extract tag",
                    "type": "union_tag_not_found",
                },
                {
                    "loc": (0, "_Sources", "datasets"),
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        )

        augmented, best_fit_types = _revalidate_undiscriminatable_items(
            errors, [{"id": "x"}], (_Building,)
        )

        assert best_fit_types == {}, "helper must not fire when concrete errors exist"
        assert augmented == errors, "errors must be left unchanged"

    def test_noop_when_original_data_is_not_a_list(self) -> None:
        """Graceful degradation: without list data there is nothing to re-home."""
        errors = cast(
            list[ValidationErrorDict],
            [
                {
                    "loc": ("tagged-union[type]",),
                    "msg": "Unable to extract tag",
                    "type": "union_tag_not_found",
                },
            ],
        )

        augmented, best_fit_types = _revalidate_undiscriminatable_items(
            errors, None, (_Building,)
        )

        assert best_fit_types == {}
        assert augmented == errors


class TestBestFitModel:
    """Tests for the `_best_fit_model` best-fit candidate selection helper."""

    def test_best_fit_model_prefers_fewest_errors(self) -> None:
        """_best_fit_model returns the candidate needing the fewest changes."""
        result = _best_fit_model({"id": "x"}, (_Place, _Building))

        assert result is not None
        model, errs = result
        # _Building needs only 'type'; _Place needs 'type' and 'name'.
        assert model is _Building
        assert len(errs) < 2
