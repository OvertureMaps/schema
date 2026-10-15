"""Tests for the discovery-to-spec bridge.

A RootModel entry point is routed by what its root denotes. A union or a
model root is a feature: `extract_model_spec` extracts it under the
wrapper's name. A scalar or container root has no record structure, so
`extract_model_spec` skips it and `extract_alias_spec` documents it as a
named alias for markdown.
"""

from codegen_test_support import (
    FeatureWithDict,
    NamedVehicleUnion,
    RenamedVehicleUnion,
    TestEnumDiscriminatorUnion,
    TollChargesByVehicleType,
)
from pydantic import RootModel

from overture.schema.codegen.extraction.field import MapOf
from overture.schema.codegen.extraction.specs import (
    NewTypeSpec,
    RecordSpec,
    UnionSpec,
)
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


def _key(cls: type) -> ModelKey:
    return ModelKey(
        name=cls.__name__.lower(),
        entry_point=f"codegen_test_support:{cls.__name__}",
        tags=frozenset(),
    )


class WrappedFeatureWithDict(RootModel[FeatureWithDict]):
    """A feature, named by a RootModel over a plain model."""


def test_union_rooted_entry_point_extracts_as_the_union() -> None:
    """A RootModel over a discriminated union is that union, named by the wrapper."""
    spec = extract_model_spec(_key(NamedVehicleUnion), NamedVehicleUnion)
    bare = extract_model_spec(_key(NamedVehicleUnion), TestEnumDiscriminatorUnion)

    assert isinstance(spec, UnionSpec)
    assert isinstance(bare, UnionSpec)
    assert spec.name == "NamedVehicleUnion"
    assert spec.description == NamedVehicleUnion.__doc__
    assert spec.members == bare.members
    assert spec.discriminator_field == bare.discriminator_field == "subtype"
    assert spec.discriminator_mapping == bare.discriminator_mapping
    assert extract_alias_spec(NamedVehicleUnion) is None


def test_nested_rootmodel_extracts_as_the_innermost_root() -> None:
    spec = extract_model_spec(_key(RenamedVehicleUnion), RenamedVehicleUnion)

    assert isinstance(spec, UnionSpec)
    assert spec.name == "RenamedVehicleUnion"
    assert spec.discriminator_field == "subtype"


def test_model_rooted_entry_point_extracts_as_the_model() -> None:
    """A RootModel over a model serializes as that model, so it is a feature."""
    spec = extract_model_spec(_key(WrappedFeatureWithDict), WrappedFeatureWithDict)
    bare = extract_model_spec(_MODEL_KEY, FeatureWithDict)

    assert isinstance(spec, RecordSpec)
    assert isinstance(bare, RecordSpec)
    assert spec.name == "WrappedFeatureWithDict"
    assert spec.description == WrappedFeatureWithDict.__doc__
    assert [f.name for f in spec.fields] == [f.name for f in bare.fields]
    assert extract_alias_spec(WrappedFeatureWithDict) is None


class UndocumentedFeatureWithDict(RootModel[FeatureWithDict]):
    pass


class UndocumentedVehicleUnion(RootModel[TestEnumDiscriminatorUnion]):
    pass


def test_undocumented_model_rooted_entry_point_keeps_the_model_description() -> None:
    """A wrapper without a docstring falls back to its root's description.

    A class does not inherit `__doc__`, so pydantic's `RootModel` docstring
    does not count as the wrapper's.
    """
    spec = extract_model_spec(
        _key(UndocumentedFeatureWithDict), UndocumentedFeatureWithDict
    )
    bare = extract_model_spec(_MODEL_KEY, FeatureWithDict)

    assert isinstance(spec, RecordSpec)
    assert isinstance(bare, RecordSpec)
    assert spec.description == bare.description == "A feature with dict fields."


def test_undocumented_union_rooted_entry_point_keeps_the_union_description() -> None:
    spec = extract_model_spec(_key(UndocumentedVehicleUnion), UndocumentedVehicleUnion)
    bare = extract_model_spec(
        _key(UndocumentedVehicleUnion), TestEnumDiscriminatorUnion
    )

    assert isinstance(spec, UnionSpec)
    assert isinstance(bare, UnionSpec)
    assert bare.description is not None
    assert spec.description == bare.description
