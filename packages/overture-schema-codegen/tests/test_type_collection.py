"""Tests for type collection module."""

from codegen_test_support import (
    FeatureWithAddress,
    FeatureWithSources,
    FeatureWithUrl,
    Instrument,
    has_name,
    lookup_by_name,
)
from overture.schema.codegen.model_extraction import expand_model_tree, extract_model
from overture.schema.codegen.specs import (
    EnumSpec,
    ModelSpec,
    NewTypeSpec,
    PydanticTypeSpec,
    SupplementarySpec,
    TypeIdentity,
)
from overture.schema.codegen.type_collection import collect_all_supplementary_types
from pydantic import BaseModel


def _make_feature_with_sub_model(sub_model: type) -> type[BaseModel]:
    """Build a feature class whose only field references sub_model."""
    return type(
        f"FeatureWith{sub_model.__name__}",
        (BaseModel,),
        {"__annotations__": {"sub": sub_model}, "sub": None},
    )


def _expanded_supplementary(model_class: type) -> dict[TypeIdentity, SupplementarySpec]:
    spec = extract_model(model_class)
    expand_model_tree(spec)
    return collect_all_supplementary_types([spec])


class TestCollectAllSupplementarySpecs:
    """Tests for collect_all_supplementary_types returning specs from expanded trees."""

    def test_returns_enum_specs(self) -> None:
        result = _expanded_supplementary(Instrument)

        assert has_name(result, "InstrumentFamily")
        assert isinstance(lookup_by_name(result, "InstrumentFamily"), EnumSpec)

    def test_returns_newtype_specs(self) -> None:
        result = _expanded_supplementary(Instrument)

        assert has_name(result, "HexColor")
        assert isinstance(lookup_by_name(result, "HexColor"), NewTypeSpec)

    def test_returns_model_specs_from_expanded_tree(self) -> None:
        result = _expanded_supplementary(FeatureWithAddress)

        assert has_name(result, "Address")
        assert isinstance(lookup_by_name(result, "Address"), ModelSpec)

    def test_collects_transitive_types(self) -> None:
        """Types referenced by sub-models are also collected."""
        result = _expanded_supplementary(FeatureWithSources)

        # Sources is a semantic NewType; SourceItem is a sub-model
        # referenced transitively via the expanded tree
        assert has_name(result, "Sources")
        assert has_name(result, "SourceItem")

    def test_same_name_different_types_both_collected(self) -> None:
        """Two types with the same __name__ from different modules are both collected."""
        ModelA = type("Address", (BaseModel,), {"__annotations__": {"x": str}})
        ModelB = type("Address", (BaseModel,), {"__annotations__": {"y": int}})

        outer_a = extract_model(_make_feature_with_sub_model(ModelA))
        expand_model_tree(outer_a)

        outer_b = extract_model(_make_feature_with_sub_model(ModelB))
        expand_model_tree(outer_b)

        result = collect_all_supplementary_types([outer_a, outer_b])

        address_entries = [
            spec for tid, spec in result.items() if tid.name == "Address"
        ]
        assert len(address_entries) == 2


class TestCollectPydanticTypes:
    """Tests for Pydantic built-in type collection."""

    def test_collects_pydantic_type_from_field(self) -> None:
        """Pydantic types referenced in fields are collected."""
        result = _expanded_supplementary(FeatureWithUrl)
        assert has_name(result, "HttpUrl")
        assert isinstance(lookup_by_name(result, "HttpUrl"), PydanticTypeSpec)

    def test_collects_pydantic_type_inside_list(self) -> None:
        """Pydantic types wrapped in list[] are collected."""
        result = _expanded_supplementary(FeatureWithUrl)
        assert has_name(result, "EmailStr")
        assert isinstance(lookup_by_name(result, "EmailStr"), PydanticTypeSpec)

    def test_does_not_collect_builtin_primitives(self) -> None:
        """Plain primitives like str are not collected as PydanticTypeSpec."""
        result = _expanded_supplementary(FeatureWithUrl)
        assert not has_name(result, "str")
        assert not has_name(result, "int")
