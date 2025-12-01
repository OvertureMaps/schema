"""Tests for CLI helper functions (load_input, perform_validation)."""

import json
from pathlib import Path

import pytest
import yaml
from click.exceptions import UsageError
from conftest import build_feature
from overture.schema.cli.commands import load_input, perform_validation, resolve_types
from pydantic import ValidationError


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
        import io

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
        model_type = resolve_types(False, None, ("buildings",), ())

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
        model_type = resolve_types(False, None, ("buildings",), ())

        with pytest.raises(ValidationError) as exc_info:
            perform_validation(data, model_type)

        errors = exc_info.value.errors()
        # Check that error location includes list index 1
        assert any(1 in error.get("loc", ()) for error in errors)

    def test_perform_validation_empty_list(self) -> None:
        """Test validating an empty list (edge case)."""
        data: list[dict[str, object]] = []
        model_type = resolve_types(False, None, ("buildings",), ())

        # Should not raise
        perform_validation(data, model_type)

    def test_perform_validation_empty_feature_collection(self) -> None:
        """Test validating an empty FeatureCollection (edge case)."""
        data = {"type": "FeatureCollection", "features": []}
        model_type = resolve_types(False, None, ("buildings",), ())

        # Should not raise
        perform_validation(data, model_type)

    def test_perform_validation_with_different_themes(self) -> None:
        """Test validating features from different themes."""
        data = build_feature(theme="buildings", type="building")

        # Should work with buildings theme
        buildings_type = resolve_types(False, None, ("buildings",), ())
        perform_validation(data, buildings_type)

        # Should fail with wrong theme
        places_type = resolve_types(False, None, ("places",), ())
        with pytest.raises(ValidationError):
            perform_validation(data, places_type)
