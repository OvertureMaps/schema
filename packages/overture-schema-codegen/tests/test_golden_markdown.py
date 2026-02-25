"""Golden-file snapshot tests for Markdown renderer output."""

from enum import Enum
from pathlib import Path

import pytest
from codegen_test_support import (
    CommonNames,
    FeatureWithAddress,
    FeatureWithDict,
    FeatureWithSources,
    HexColor,
    Id,
    Instrument,
    InstrumentFamily,
    SimpleKind,
    Sources,
    Venue,
    Widget,
    assert_golden,
)
from overture.schema.codegen.enum_extraction import extract_enum
from overture.schema.codegen.markdown_renderer import (
    render_enum,
    render_feature,
    render_newtype,
)
from overture.schema.codegen.model_extraction import expand_model_tree, extract_model
from overture.schema.codegen.newtype_extraction import extract_newtype
from overture.schema.codegen.reverse_references import (
    UsedByEntry,
    compute_reverse_references,
)
from overture.schema.codegen.type_collection import collect_all_supplementary_types
from pydantic import BaseModel

GOLDEN_DIR = Path(__file__).parent / "golden" / "markdown"

FEATURE_CASES = [
    (Instrument, "instrument.md"),
    (Venue, "venue.md"),
    (Widget, "widget.md"),
    (FeatureWithSources, "feature_with_sources.md"),
    (FeatureWithAddress, "feature_with_address.md"),
    (FeatureWithDict, "feature_with_dict.md"),
]

ENUM_CASES = [
    (InstrumentFamily, "instrument_family.md"),
    (SimpleKind, "simple_kind.md"),
]

NEWTYPE_CASES = [
    (HexColor, "hex_color.md"),
    (Id, "id.md"),
    (Sources, "sources.md"),
    (CommonNames, "common_names.md"),
]


@pytest.fixture(scope="module")
def reverse_refs() -> dict[str, list[UsedByEntry]]:
    """Compute reverse references for all test models."""
    feature_specs = []
    for model_class, _ in FEATURE_CASES:
        assert isinstance(model_class, type) and issubclass(model_class, BaseModel)
        spec = extract_model(model_class)
        expand_model_tree(spec)
        feature_specs.append(spec)

    all_specs = collect_all_supplementary_types(feature_specs)
    return compute_reverse_references(feature_specs, all_specs)


@pytest.mark.parametrize(
    ("model_class", "golden_filename"),
    FEATURE_CASES,
    ids=[name for _, name in FEATURE_CASES],
)
def test_feature_golden(
    model_class: type[BaseModel],
    golden_filename: str,
    update_golden: bool,
    reverse_refs: dict[str, list[UsedByEntry]],
) -> None:
    spec = extract_model(model_class)
    expand_model_tree(spec)
    used_by = reverse_refs.get(spec.name)
    actual = render_feature(spec, used_by=used_by)
    assert_golden(actual, GOLDEN_DIR / golden_filename, update=update_golden)


@pytest.mark.parametrize(
    ("enum_class", "golden_filename"),
    ENUM_CASES,
    ids=[name for _, name in ENUM_CASES],
)
def test_enum_golden(
    enum_class: type[Enum],
    golden_filename: str,
    update_golden: bool,
    reverse_refs: dict[str, list[UsedByEntry]],
) -> None:
    spec = extract_enum(enum_class)
    used_by = reverse_refs.get(spec.name)
    actual = render_enum(spec, used_by=used_by)
    assert_golden(actual, GOLDEN_DIR / golden_filename, update=update_golden)


@pytest.mark.parametrize(
    ("newtype_callable", "golden_filename"),
    NEWTYPE_CASES,
    ids=[name for _, name in NEWTYPE_CASES],
)
def test_newtype_golden(
    newtype_callable: object,
    golden_filename: str,
    update_golden: bool,
    reverse_refs: dict[str, list[UsedByEntry]],
) -> None:
    spec = extract_newtype(newtype_callable)
    used_by = reverse_refs.get(spec.name)
    actual = render_newtype(spec, used_by=used_by)
    assert_golden(actual, GOLDEN_DIR / golden_filename, update=update_golden)
