"""Unit tests for `typing_util`, the shared type-expression helpers."""

import types
from enum import Enum
from typing import Annotated, ForwardRef, Literal, NewType, Union

import pytest
from pydantic import BaseModel, Discriminator, Field, Tag, TypeAdapter
from pydantic.experimental.missing_sentinel import MISSING
from pydantic.fields import FieldInfo

from overture.schema.system.optionality import Omitable
from overture.schema.system.typing_util import (
    accepts_none,
    is_model_union,
    is_newtype,
    model_types,
    model_variants,
    non_model_parts,
    resolves_to_models,
    root_annotated_metadata,
    single_literal_value,
    union_discriminator,
)


class Target(BaseModel):
    name: str


class OtherTarget(BaseModel):
    label: str


class RoadThing(BaseModel):
    type: Literal["thing"] = "thing"
    subtype: Literal["road"] = "road"


class RailThing(BaseModel):
    type: Literal["thing"] = "thing"
    subtype: Literal["rail"] = "rail"


class WaterThing(BaseModel):
    type: Literal["thing"] = "thing"
    subtype: Literal["water"] = "water"


# A Segment-shaped discriminated union alias: tagged arms behind a discriminator.
Thing = Annotated[
    Annotated[RoadThing, Tag("road")]
    | Annotated[RailThing, Tag("rail")]
    | Annotated[WaterThing, Tag("water")],
    Field(discriminator="subtype"),
]


# ---------------------------------------------------------------------------
# model_types / non_model_parts
# ---------------------------------------------------------------------------


def test_bare_class() -> None:
    assert model_types(Target) == (Target,)
    assert non_model_parts(Target) == ()
    assert is_model_union(Target) is False
    assert union_discriminator(Target) is None
    assert root_annotated_metadata(Target) == ()


def test_annotated_single_model() -> None:
    marker = Field()
    tp = Annotated[Target, marker]
    assert model_types(tp) == (Target,)
    assert root_annotated_metadata(tp) == (marker,)
    assert union_discriminator(tp) is None


def test_plain_union() -> None:
    tp = Target | OtherTarget
    assert model_types(tp) == (Target, OtherTarget)
    assert is_model_union(tp) is True
    assert union_discriminator(tp) is None


def test_newtype() -> None:
    Aliased = NewType("Aliased", Target)
    assert model_types(Aliased) == (Target,)


def test_partial_model_union_records_non_model_parts() -> None:
    tp = Target | int
    assert model_types(tp) == (Target,)
    assert non_model_parts(tp) == (int,)
    assert is_model_union(tp) is False


def test_unrecognized_expression() -> None:
    assert model_types("not a type") == ()
    assert non_model_parts("not a type") == ("not a type",)
    assert is_model_union("not a type") is False


def test_unevaluated_forward_ref_raises() -> None:
    # Silently treating a forward reference as a non-model leaf would make models
    # behind unresolved references vanish from discovery and validation.
    tp = Union["NotDefinedAnywhere", Target]  # type: ignore[name-defined] # noqa: F821
    with pytest.raises(TypeError, match="forward reference"):
        model_types(tp)
    with pytest.raises(TypeError, match="NotDefinedAnywhere"):
        model_types(ForwardRef("NotDefinedAnywhere"))


# ---------------------------------------------------------------------------
# union_discriminator / model_variants
# ---------------------------------------------------------------------------


def test_discriminated_union_alias() -> None:
    assert model_types(Thing) == (RoadThing, RailThing, WaterThing)
    assert is_model_union(Thing) is True
    assert union_discriminator(Thing) == "subtype"
    assert all(arm.discriminator_path == ("subtype",) for arm in model_variants(Thing))
    # The discriminator FieldInfo itself is retained as root metadata.
    assert any(
        isinstance(meta, FieldInfo) and meta.discriminator == "subtype"
        for meta in root_annotated_metadata(Thing)
    )


def test_nested_discriminated_union() -> None:
    Nested = Annotated[
        Annotated[Thing, Tag("thing")] | Annotated[Target, Tag("target")],
        Field(discriminator="type"),
    ]
    assert union_discriminator(Nested) == "type"
    assert model_types(Nested) == (RoadThing, RailThing, WaterThing, Target)
    by_model = {arm.model: arm for arm in model_variants(Nested)}
    assert by_model[RoadThing].discriminator_path == ("type", "subtype")
    assert by_model[Target].discriminator_path == ("type",)


def test_arm_discriminator_not_promoted_to_root() -> None:
    # A plain union containing a discriminated alias arm is itself not discriminated.
    tp = Thing | Target
    assert union_discriminator(tp) is None
    by_model = {arm.model: arm for arm in model_variants(tp)}
    # The arm-level discriminator is still recorded on the arms it governs.
    assert by_model[RoadThing].discriminator_path == ("subtype",)
    assert by_model[Target].discriminator_path == ()


def test_newtype_over_union_alias() -> None:
    AliasedThing = NewType("AliasedThing", Thing)  # type: ignore[valid-newtype]
    assert model_types(AliasedThing) == (RoadThing, RailThing, WaterThing)
    assert union_discriminator(AliasedThing) == "subtype"


def test_discriminator_object_form() -> None:
    tp = Annotated[RoadThing | RailThing, Field(discriminator=Discriminator("subtype"))]
    assert union_discriminator(tp) == "subtype"


def test_bare_discriminator_metadata() -> None:
    # Pydantic's direct `Annotated[..., Discriminator("subtype")]` form, without Field.
    tp = Annotated[RoadThing | RailThing, Discriminator("subtype")]
    assert union_discriminator(tp) == "subtype"
    assert all(arm.discriminator_path == ("subtype",) for arm in model_variants(tp))


def test_bare_discriminator_callable() -> None:
    def by_subtype(value: object) -> str:
        return "road"

    by_subtype._field_name = "subtype"  # type: ignore[attr-defined]
    tp = Annotated[RoadThing | RailThing, Discriminator(by_subtype)]
    assert union_discriminator(tp) == "subtype"


class First(BaseModel):
    inner: Literal["first"]
    outer: Literal["first"]


class Second(BaseModel):
    inner: Literal["second"]
    outer: Literal["second"]


Stacked = Annotated[
    Annotated[First | Second, Field(discriminator="inner")],
    Field(discriminator="outer"),
]


def test_uses_outermost_stacked_discriminator() -> None:
    assert union_discriminator(Stacked) == "outer"
    assert all(arm.discriminator_path == ("outer",) for arm in model_variants(Stacked))


# ---------------------------------------------------------------------------
# Cross-check against Pydantic's own interpretation. `TypeAdapter`'s schema is
# the canonical answer to "is this a tagged union and on what field" -- these
# pin the walker to Pydantic's semantics for every discriminator form we handle.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tp",
    [
        pytest.param(Thing, id="field-discriminator-string"),
        pytest.param(
            Annotated[
                RoadThing | RailThing, Field(discriminator=Discriminator("subtype"))
            ],
            id="field-discriminator-object",
        ),
        pytest.param(
            Annotated[RoadThing | RailThing, Discriminator("subtype")],
            id="bare-discriminator",
        ),
        pytest.param(Stacked, id="stacked-discriminators"),
    ],
)
def test_union_discriminator_matches_pydantic_schema(tp: object) -> None:
    pydantic_discriminator = TypeAdapter(tp).json_schema()["discriminator"][
        "propertyName"
    ]
    assert union_discriminator(tp) == pydantic_discriminator


def test_union_discriminator_none_matches_pydantic_schema() -> None:
    tp = Target | OtherTarget
    assert "discriminator" not in TypeAdapter(tp).json_schema()
    assert union_discriminator(tp) is None


# ---------------------------------------------------------------------------
# Vacuous union arms (None / sentinels)
# ---------------------------------------------------------------------------


def test_optional_model_union_is_model_union() -> None:
    assert is_model_union(Target | OtherTarget | None) is True
    assert model_types(Target | OtherTarget | None) == (Target, OtherTarget)


def test_omitable_model_union_is_model_union() -> None:
    assert is_model_union(Omitable[Target | OtherTarget]) is True
    assert model_types(Omitable[Target | OtherTarget]) == (Target, OtherTarget)


def test_optional_single_model_is_not_a_union() -> None:
    # Vacuous arms reducing a union to one real arm make the frame transparent:
    # `Target | None` is an optional model, never a one-member union.
    assert is_model_union(Target | None) is False
    assert is_model_union(Omitable[Target]) is False
    assert model_types(Target | None) == (Target,)


def test_non_model_parts_keeps_elided_members() -> None:
    # Strict callers (extension targets, json_schema) reject optionality; the
    # vacuous arms therefore stay visible here.
    assert non_model_parts(Target | None) == (types.NoneType,)
    assert non_model_parts(Target | OtherTarget | None) == (types.NoneType,)
    assert non_model_parts(Omitable[Target])[0] is MISSING


def test_resolves_to_models() -> None:
    assert resolves_to_models(Target) is True
    assert resolves_to_models(Target | None) is True
    assert resolves_to_models(Omitable[Target | OtherTarget]) is True
    assert resolves_to_models(Target | int) is False
    assert resolves_to_models(int) is False
    assert resolves_to_models(Literal["x"]) is False


def test_optional_union_discriminator_is_reported() -> None:
    # The optional frame is transparent, so the alias's discriminator is the
    # expression's discriminator (diverging from pydantic's anyOf JSON schema).
    tp = Annotated[RoadThing | RailThing, Field(discriminator="subtype")] | None
    assert union_discriminator(tp) == "subtype"
    assert [arm.discriminator_path for arm in model_variants(tp)] == [
        ("subtype",),
        ("subtype",),
    ]


def test_optional_union_metadata_is_reported() -> None:
    marker = Field(description="alias docs", discriminator="subtype")
    tp = Annotated[RoadThing | RailThing, marker] | None
    assert marker in root_annotated_metadata(tp)


# ---------------------------------------------------------------------------
# single_literal_value
# ---------------------------------------------------------------------------


class _Kind(str, Enum):
    ROAD = "road"


def test_single_literal_value_forms() -> None:
    assert single_literal_value(Literal["x"]) == "x"
    assert single_literal_value(Annotated[Literal["x"], "meta"]) == "x"
    assert single_literal_value(Literal["x"] | None) == "x"
    assert single_literal_value(NewType("N", Literal["x"])) == "x"
    # Raw value: an Enum member comes back as the member, not its .value.
    assert single_literal_value(Literal[_Kind.ROAD]) is _Kind.ROAD


def test_single_literal_value_absent() -> None:
    assert single_literal_value(Literal["x", "y"]) is None
    assert single_literal_value(str) is None
    assert single_literal_value("garbage") is None
    assert single_literal_value(Target | OtherTarget) is None
    # Literal[None] deliberately collapses to "no single literal".
    assert single_literal_value(Literal[None]) is None


def test_accepts_none() -> None:
    assert accepts_none(Target | None) is True
    assert accepts_none(Annotated[Target | None, "meta"] | OtherTarget) is True
    assert accepts_none(Target | OtherTarget) is False
    # Sentinels express omissibility, not None acceptance.
    assert accepts_none(Omitable[Target]) is False
    # Containers are opaque: element nullability is not field optionality.
    assert accepts_none(list[Target | None]) is False


def test_unresolved_forward_ref_policy_split() -> None:
    # Built via an explicit ForwardRef so mypy doesn't try to resolve the name.
    unresolved: object = Union[Target, ForwardRef("NeverDefinedAnywhere")]  # type: ignore[valid-type]  # noqa: UP007
    # Boolean predicates answer conservatively instead of raising.
    assert is_model_union(unresolved) is False
    assert resolves_to_models(unresolved) is False
    # Optionality/metadata questions ignore opaque refs.
    assert accepts_none(unresolved) is False
    assert (
        accepts_none(
            Union[Target, ForwardRef("NeverDefined"), None]  # type: ignore[valid-type]  # noqa: UP007
        )
        is True
    )
    # Strict parts reporting includes the unresolved ref.
    assert any(isinstance(p, ForwardRef) for p in non_model_parts(unresolved))
    # Model accessors stay strict.
    with pytest.raises(TypeError, match="Unevaluated forward reference"):
        model_types(unresolved)
    with pytest.raises(TypeError, match="Unevaluated forward reference"):
        model_variants(unresolved)


def test_typing_extensions_newtype_recognized() -> None:
    import typing_extensions

    Aliased = typing_extensions.NewType("Aliased", Target)
    assert is_newtype(Aliased) is True
    assert is_newtype(NewType("N", int)) is True
    assert is_newtype(int) is False
    # The walker and the literal peel see through it like typing.NewType.
    assert model_types(Aliased) == (Target,)
    LitAlias = typing_extensions.NewType("LitAlias", Literal["x"])  # type: ignore[valid-newtype]
    assert single_literal_value(LitAlias) == "x"
