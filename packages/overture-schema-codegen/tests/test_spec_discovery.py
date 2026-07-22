"""Tests for the discovery-to-spec bridge.

A RootModel entry point splits by output: it has no record structure, so
`extract_model_spec` skips it (dropping it from expression generation),
while `extract_alias_spec` documents it as a named alias for markdown.
"""

from codegen_test_support import FeatureWithDict, TollChargesByVehicleType
from overture.schema.codegen.extraction.field import MapOf
from overture.schema.codegen.extraction.specs import NewTypeSpec, RecordSpec
from overture.schema.codegen.spec_discovery import (
    extract_alias_spec,
    extract_model_spec,
)
from overture.schema.system.discovery import ModelKey

_ROOTMODEL_KEY = ModelKey(
    name="toll_charges",
    entry_point="codegen_test_support:TollChargesByVehicleType",
    tags=frozenset(),
)
_MODEL_KEY = ModelKey(
    name="dictfeat",
    entry_point="codegen_test_support:FeatureWithDict",
    tags=frozenset(),
)


def test_rootmodel_entry_point_is_not_a_model_spec() -> None:
    """A RootModel produces no `ModelSpec`, so expression generation skips it.

    A RootModel serializes as its bare root value and has no record
    structure, so extracting it as a top-level `RecordSpec` would invent a
    spurious `root` column. `extract_model_spec` returns None so it drops
    out of the feature/union specs the pipelines consume.
    """
    assert extract_model_spec(_ROOTMODEL_KEY, TollChargesByVehicleType) is None


def test_rootmodel_entry_point_extracts_alias_spec() -> None:
    """A RootModel entry point documents as a `NewTypeSpec` alias.

    Entry points contribute custom classes, not only tables: an extension
    may register a RootModel as a type used as a field elsewhere. So the
    markdown side documents it as a named alias over its bare root shape.
    """
    spec = extract_alias_spec(TollChargesByVehicleType)

    assert isinstance(spec, NewTypeSpec)
    assert spec.name == "TollChargesByVehicleType"
    assert isinstance(spec.shape, MapOf)


def test_non_rootmodel_entry_point_has_no_alias() -> None:
    """A plain model contributes no alias -- it is a feature, not an alias."""
    assert extract_alias_spec(FeatureWithDict) is None
    assert isinstance(extract_model_spec(_MODEL_KEY, FeatureWithDict), RecordSpec)
