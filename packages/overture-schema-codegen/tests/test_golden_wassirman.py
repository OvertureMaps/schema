"""Golden-file snapshot tests for wassirman validation IR output."""

from pathlib import Path

import pytest
from codegen_test_support import assert_golden
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.specs import (
    FeatureSpec,
    is_model_class,
    is_union_alias,
)
from overture.schema.codegen.extraction.union_extraction import extract_union
from overture.schema.codegen.layout.module_layout import entry_point_class
from overture.schema.codegen.wassirman.pipeline import generate_validation_ir
from overture.schema.core.discovery import ModelKey, discover_models

GOLDEN_DIR = Path(__file__).parent / "golden" / "wassirman"


def _entry_name(key: ModelKey, entry: object) -> str:
    if isinstance(entry, type):
        return entry.__name__
    return entry_point_class(key.entry_point)


@pytest.fixture(scope="module")
def all_models() -> dict:
    return discover_models()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize from discovered models so new types are picked up automatically."""
    if "model_name" not in metafunc.fixturenames:
        return
    models = discover_models()
    cases = [
        (_entry_name(key, entry), f"{_entry_name(key, entry).lower()}.yaml")
        for key, entry in models.items()
    ]
    metafunc.parametrize(
        ("model_name", "golden_filename"),
        cases,
        ids=[name for name, _ in cases],
    )


def test_wassirman_golden(
    model_name: str,
    golden_filename: str,
    update_golden: bool,
    all_models: dict,
) -> None:
    spec: FeatureSpec | None = None
    for key, entry in all_models.items():
        if _entry_name(key, entry) == model_name:
            if is_model_class(entry):
                spec = extract_model(entry, entry_point=key.entry_point)
            elif is_union_alias(entry):
                spec = extract_union(
                    entry_point_class(key.entry_point),
                    entry,
                    entry_point=key.entry_point,
                )
            break
    if spec is None:
        pytest.fail(f"Model {model_name} not found in discovered models")

    ir = generate_validation_ir([spec])
    actual = ir.to_yaml()
    assert_golden(actual, GOLDEN_DIR / golden_filename, update=update_golden)
