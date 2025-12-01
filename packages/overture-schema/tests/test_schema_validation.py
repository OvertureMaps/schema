import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml
from overture.schema import validate, validate_json
from pydantic import ValidationError
from yamlcore import CoreLoader  # type: ignore

# Top-level constants for paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "reference" / "examples"
COUNTEREXAMPLES_DIR = PROJECT_ROOT / "reference" / "counterexamples"


def load_example_file(file_path: str) -> Any:
    """Load a feature from JSON or YAML file and return flattened/tabular format."""
    with open(file_path, encoding="utf-8") as f:
        # use a YAML-1.2-compliant (which dropped support for yes/no boolean values) Loader
        return yaml.load(f, Loader=CoreLoader)


def create_flat_variant(feature: dict[str, Any]) -> dict[str, Any]:
    """Create a variant of the feature with flat/Parquet-style structure."""
    flat_feature = feature.copy()

    # Check if this is GeoJSON format that needs flattening
    if "properties" in flat_feature and flat_feature.get("type") == "Feature":
        # Flatten GeoJSON feature to match GeoParquet structure
        flat_feature.update(flat_feature["properties"])
        del flat_feature["properties"]
        # Remove the GeoJSON "type": "Feature" field
        if flat_feature.get("type") == "Feature":
            del flat_feature["type"]

    return flat_feature


def walk_directory(directory: Path) -> Generator[Path, None, None]:
    """Walk directory and yield all relevant files, including those in .disabled
    directories."""
    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.suffix in {
            ".json",
            ".geojson",
            ".yaml",
            ".yml",
            ".disabled",
        }:
            yield file_path


def group_files_by_directory(files: list[Path], base_dir: Path) -> dict[str, Any]:
    """Group files by their directory structure."""
    groups: dict[str, Any] = {}

    for file_path in files:
        relative_path = file_path.relative_to(base_dir)
        parts = relative_path.parts

        if len(parts) == 1:
            # File in root directory
            if "" not in groups:
                groups[""] = []
            groups[""].append(str(file_path))
            continue

        # Navigate through directory parts
        current = groups
        dir_parts = parts[:-1]

        for part in dir_parts:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Add file to final directory
        last_dir = dir_parts[-1] if dir_parts else ""
        if not isinstance(current.get(last_dir), list):
            current[last_dir] = []
        current[last_dir].append(str(file_path))

    return groups


def create_test_cases(
    group: dict[str, Any], base_dir: Path
) -> list[tuple[str, str, bool]]:
    """Create test cases from grouped files."""
    test_cases = []

    def collect_files(g: dict[str, Any], prefix: str = "") -> None:
        for name, value in g.items():
            if isinstance(value, list):
                # Files in this directory
                for file_path in value:
                    display_path = str(Path(file_path).relative_to(base_dir))
                    # Check if any part of the path contains .disabled
                    is_disabled = any(
                        part.endswith(".disabled") for part in Path(file_path).parts
                    )
                    test_name = (
                        f"{prefix}{name}/{display_path}" if prefix else display_path
                    )
                    test_cases.append((test_name, file_path, is_disabled))
            else:
                # Nested directory
                new_prefix = f"{prefix}{name}/" if prefix else f"{name}/"
                collect_files(value, new_prefix)

    collect_files(group)
    return test_cases


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Generate parameterized tests for examples and counterexamples."""
    if "example_file" in metafunc.fixturenames:
        # Generate tests for examples (should pass validation)
        if EXAMPLES_DIR.exists():
            example_files = list(walk_directory(EXAMPLES_DIR))
            grouped_examples = group_files_by_directory(example_files, EXAMPLES_DIR)
            test_cases = create_test_cases(grouped_examples, EXAMPLES_DIR)

            # Create parameter values with marks for enabled/disabled tests
            param_values = []

            for name, path, disabled in test_cases:
                if disabled:
                    param_values.append(
                        pytest.param(
                            path,
                            id=name,
                            marks=pytest.mark.skip(reason="Test disabled"),
                        )
                    )
                else:
                    param_values.append(pytest.param(path, id=name))

            metafunc.parametrize("example_file", param_values)

    elif "counterexample_file" in metafunc.fixturenames:
        # Generate tests for counterexamples (should fail validation)
        if COUNTEREXAMPLES_DIR.exists():
            counterexample_files = list(walk_directory(COUNTEREXAMPLES_DIR))
            grouped_counterexamples = group_files_by_directory(
                counterexample_files, COUNTEREXAMPLES_DIR
            )
            test_cases = create_test_cases(grouped_counterexamples, COUNTEREXAMPLES_DIR)

            # Create parameter values with marks for enabled/disabled tests
            param_values = []

            for name, path, disabled in test_cases:
                if disabled:
                    param_values.append(
                        pytest.param(
                            path,
                            id=name,
                            marks=pytest.mark.skip(reason="Test disabled"),
                        )
                    )
                else:
                    param_values.append(pytest.param(path, id=name))

            metafunc.parametrize("counterexample_file", param_values)


def test_example_validation_json(example_file: str) -> None:
    """
    Test that examples pass validation with JSON input format. This will test GeoJSON parsing for
    examples based on GeoJSON features.
    """
    json_input = load_example_file(example_file)

    try:
        model = validate_json(json.dumps(json_input))
    except Exception as e:
        raise pytest.fail.Exception(
            f"Example failed validation (JSON): {example_file}"
        ) from e

    # If validation passed and we have a parsed feature, serialize to JSON and compare with the
    # original JSON.
    json_dump = model.model_dump(exclude_unset=True, by_alias=True, mode="json")
    assert json_dump == json_input, (
        f"Dumped model JSON differs from original: {example_file}"
    )


def test_example_validation_flat(example_file: str) -> None:
    """
    Test that examples pass validation with Python input format, which should have the same
    structure as Parquet.
    """
    json_input = load_example_file(example_file)
    flat_input = create_flat_variant(json_input)

    try:
        model = validate(flat_input)
    except Exception as e:
        raise pytest.fail.Exception(
            f"example failed validation (Python): {example_file}"
        ) from e

    # If validation passed and we have a parsed feature, serialize back to both the flattened mode
    # and JSON and verify no differences.
    json_dump = model.model_dump(exclude_unset=True, by_alias=True, mode="json")
    assert json_dump == json_input, (
        f"Dumped model JSON differs from original: {example_file}"
    )


def test_counterexample_validation_json(counterexample_file: str) -> None:
    """
    Test that counterexamples fail validation with JSON input format. This will test GeoJSON
    validation for counterexamples based on GeoJSON features.
    """
    json_input = load_example_file(counterexample_file)

    is_valid = False
    try:
        validate_json(json.dumps(json_input))
        is_valid = True
    except ValidationError:
        pass

    assert not is_valid, (
        f"Counterexample should have failed validation (JSON): {counterexample_file}"
    )


def test_counterexample_validation_flat(counterexample_file: str) -> None:
    """Test that counterexamples fail validation with flat input format."""
    json_input = load_example_file(counterexample_file)
    flat_input = create_flat_variant(json_input)

    is_valid = False
    try:
        validate(flat_input)
        is_valid = True
    except ValidationError:
        pass

    assert not is_valid, (
        f"Counterexample should have failed validation (Python): {counterexample_file}"
    )
