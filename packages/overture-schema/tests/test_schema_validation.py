from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml
from deepdiff import DeepDiff
from overture.schema import parse
from yamlcore import CoreLoader  # type: ignore

# Top-level constants for paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "reference" / "examples"
COUNTEREXAMPLES_DIR = PROJECT_ROOT / "reference" / "counterexamples"


def load_feature(file_path: str) -> dict[str, Any]:
    """Load a feature from JSON or YAML file and return flattened/tabular format."""
    with open(file_path, encoding="utf-8") as f:
        # use a YAML-1.2-compliant (which dropped support for yes/no boolean values) Loader
        feature = yaml.load(f, Loader=CoreLoader)
        return create_flat_variant(feature)


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


def convert_to_geojson_format(flattened_feature: dict[str, Any]) -> dict[str, Any]:
    """Convert flattened feature to GeoJSON format for comparison."""
    return {
        "type": "Feature",
        "id": flattened_feature.get("id", None),
        "geometry": flattened_feature.get("geometry", None),
        "properties": {
            k: v for k, v in flattened_feature.items() if k not in ["id", "geometry"]
        },
    }


def deep_compare_dicts(
    original: dict[str, Any], parsed: dict[str, Any]
) -> tuple[bool, str]:
    """Perform deep comparison between original and parsed dictionaries.

    Returns (is_equal, differences_report).
    """
    diff = DeepDiff(original, parsed, ignore_order=True, significant_digits=15)

    if not diff:
        return True, ""

    # Format differences for readable output
    differences = []

    if "values_changed" in diff:
        differences.append("Value changes:")
        for key, change in diff["values_changed"].items():
            differences.append(
                f"  {key}: {change['old_value']} -> {change['new_value']}"
            )

    if "dictionary_item_added" in diff:
        differences.append("Added items:")
        for item in diff["dictionary_item_added"]:
            differences.append(f"  {item}")

    if "dictionary_item_removed" in diff:
        differences.append("Removed items:")
        for item in diff["dictionary_item_removed"]:
            differences.append(f"  {item}")

    if "type_changes" in diff:
        differences.append("Type changes:")
        for key, change in diff["type_changes"].items():
            differences.append(f"  {key}: {change['old_type']} -> {change['new_type']}")

    return False, "\n".join(differences)


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
    group: dict[str, Any], base_dir: Path, is_counterexample: bool = False
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
            test_cases = create_test_cases(
                grouped_examples, EXAMPLES_DIR, is_counterexample=False
            )

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
            test_cases = create_test_cases(
                grouped_counterexamples, COUNTEREXAMPLES_DIR, is_counterexample=True
            )

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


def test_example_validation_geojson(example_file: str) -> None:
    """Test that examples pass validation with GeoJSON input format."""
    feature = load_feature(example_file)

    if "geometry" not in feature:
        pytest.skip("Example does not have a geometry field")

    test_feature = convert_to_geojson_format(feature)

    is_valid = False
    error_msg = None
    try:
        parsed_feature = parse(test_feature)
        is_valid = True
    except Exception as e:
        error_msg = e

    assert is_valid, (
        f"Example failed validation (geojson): {example_file}\nError: {error_msg}"
    )

    # If validation passed and we have a parsed feature, compare with GeoJSON format
    if parsed_feature is not None:
        # Parsed feature should be in GeoJSON format, so compare directly
        is_equal, diff_report = deep_compare_dicts(test_feature, parsed_feature)
        assert is_equal, (
            f"Parsed feature differs from original (geojson): {example_file}\n"
            f"Differences:\n{diff_report}"
        )


def test_example_validation_flat(example_file: str) -> None:
    """Test that examples pass validation with flat/Parquet-style input."""
    flat_feature = load_feature(example_file)  # Load as flat (authoritative)
    test_feature = flat_feature  # Use flat format directly

    is_valid = False
    error_msg = None
    try:
        parsed_feature = parse(test_feature)
        is_valid = True
    except Exception as e:
        error_msg = e

    assert is_valid, (
        f"Example failed validation (flat): {example_file}\nError: {error_msg}"
    )

    # If validation passed and we have a parsed feature, compare with GeoJSON format
    if parsed_feature is not None and "geometry" in flat_feature:
        # Parsed feature should be in GeoJSON format, so compare with GeoJSON variant
        expected_geojson = convert_to_geojson_format(flat_feature)
        is_equal, diff_report = deep_compare_dicts(expected_geojson, parsed_feature)
        assert is_equal, (
            f"Parsed feature differs from expected (flat): {example_file}\n"
            f"Differences:\n{diff_report}"
        )


def test_counterexample_validation_geojson(counterexample_file: str) -> None:
    """Test that counterexamples fail validation with GeoJSON input format."""
    flat_feature = load_feature(counterexample_file)  # Load as flat (authoritative)
    test_feature = convert_to_geojson_format(flat_feature)  # Convert to GeoJSON format

    is_valid = False
    try:
        parse(test_feature)
        is_valid = True
    except Exception:
        pass

    assert not is_valid, (
        f"Counterexample should have failed validation (geojson): {counterexample_file}"
    )


def test_counterexample_validation_flat(counterexample_file: str) -> None:
    """Test that counterexamples fail validation with flat input format."""
    flat_feature = load_feature(counterexample_file)  # Load as flat (authoritative)
    test_feature = flat_feature  # Use flat format directly

    is_valid = False
    try:
        parse(test_feature)
        is_valid = True
    except Exception:
        pass

    assert not is_valid, (
        f"Counterexample should have failed validation (flat): {counterexample_file}"
    )
