"""Golden file comparison helpers for baseline tests."""

import json
from difflib import unified_diff
from pathlib import Path

from overture.schema.system.json_schema import json_schema


def assert_golden(actual: str, golden_path: Path, *, update: bool) -> None:
    """Compare actual output against a golden file.

    Parameters
    ----------
    actual
        Generated content to compare.
    golden_path
        Path to the golden file.
    update
        When True, write actual to golden_path instead of comparing.
    """
    if update:
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(actual)
        return
    if not golden_path.exists():
        raise AssertionError(
            f"Golden file not found: {golden_path}\n"
            "Run 'make update-baselines' to generate it."
        )
    expected = golden_path.read_text()
    if actual != expected:
        diff = "\n".join(
            unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=str(golden_path),
                tofile="actual",
                lineterm="",
            )
        )
        raise AssertionError(f"Golden file mismatch:\n{diff}")


def assert_json_schema_golden(
    model_or_union: object, golden_path: Path, *, update: bool
) -> None:
    """Generate JSON Schema and compare against a golden file.

    Parameters
    ----------
    model_or_union
        Pydantic model class or union type alias.
    golden_path
        Path to the baseline JSON file.
    update
        When True, write generated schema to golden_path instead of comparing.
    """
    schema = json_schema(model_or_union)
    actual = json.dumps(schema, indent=2, sort_keys=True)
    assert_golden(actual, golden_path, update=update)
