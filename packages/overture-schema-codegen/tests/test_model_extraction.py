"""Tests for `extract_model`."""

from typing import Annotated, Literal, Optional

from annotated_types import Ge
from codegen_test_support import FeatureWithRootModel
from overture.schema.codegen.extraction.field import (
    ArrayOf,
    MapOf,
    ModelRef,
    Primitive,
    UnionRef,
)
from overture.schema.codegen.extraction.field_walk import terminal_of
from overture.schema.codegen.extraction.length_constraints import ArrayMinLen
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.common.scoping.vehicle import VehicleSelector
from overture.schema.system.extension import Extends
from pydantic import BaseModel, Field, RootModel


def test_extract_model_populates_union_terminal() -> None:
    """`extract_model` resolves UNION terminals to a `UnionRef` carrying a `UnionSpec`."""

    class Container(BaseModel):
        items: list[VehicleSelector]

    spec = extract_model(Container)
    items_field = next(f for f in spec.fields if f.name == "items")

    terminal = terminal_of(items_field.shape)
    assert isinstance(terminal, UnionRef)
    assert terminal.union.discriminator_field == "dimension"


def test_rootmodel_field_extracts_bare_root() -> None:
    """A `RootModel`-typed field extracts to its bare root shape.

    Pydantic validates and serializes a RootModel as its bare root value,
    so extraction must not produce a `ModelRef` struct with a synthetic
    `root` member -- the generated schema would then declare a wrapper the
    data never carries.
    """
    spec = extract_model(FeatureWithRootModel)
    toll = next(f for f in spec.fields if f.name == "toll_charges")

    assert isinstance(toll.shape, MapOf)
    assert toll.is_optional is True


def test_required_list_with_optional_element_is_required() -> None:
    """A required `list[X | None]` field must not inherit element optionality.

    `list[str | None]` is a list whose elements may be None; the field
    itself still requires a list to be present. The list branch must
    return `False` for field optionality so `FieldSpec.is_required` stays
    `True` and `check_required` is generated for the field.
    """

    class M(BaseModel):
        tags: list[str | None]

    spec = extract_model(M)
    tags_field = next(f for f in spec.fields if f.name == "tags")

    assert tags_field.is_optional is False
    assert tags_field.is_required is True
    assert isinstance(tags_field.shape, ArrayOf)
    assert isinstance(tags_field.shape.element, Primitive)
    assert tags_field.shape.element.base_type == "str"


def test_required_list_plain_element_is_required() -> None:
    """A required `list[str]` field is unaffected by the optionality fix."""

    class M(BaseModel):
        tags: list[str]

    spec = extract_model(M)
    tags_field = next(f for f in spec.fields if f.name == "tags")

    assert tags_field.is_optional is False
    assert tags_field.is_required is True
    assert isinstance(tags_field.shape, ArrayOf)


def test_optional_list_with_optional_element_is_optional() -> None:
    """A `list[str | None] | None` field is optional (the outer | None)."""

    class M(BaseModel):
        tags: list[str | None] | None = None

    spec = extract_model(M)
    tags_field = next(f for f in spec.fields if f.name == "tags")

    assert tags_field.is_optional is True
    assert tags_field.is_required is False


def test_self_referential_list_forward_ref_resolves_to_cycle() -> None:
    """A `list["Self"]` forward ref resolves to a cycle-marked `ModelRef`.

    Builtin generics store `list["Node"]`'s element as a bare `str`,
    which neither Pydantic nor `typing.get_type_hints` resolves.
    `extract_model` must resolve it against the model's namespace so the
    self-reference reaches its model terminal and the cycle guard marks
    the back-edge -- rather than crashing the type analyzer's terminal
    classifier on an unresolved string.
    """

    class Node(BaseModel):
        val: Annotated[int, Field(ge=0)]
        children: list["Node"] = Field(default_factory=list)

    spec = extract_model(Node)
    children = next(f for f in spec.fields if f.name == "children")

    assert isinstance(children.shape, ArrayOf)
    element = children.shape.element
    assert isinstance(element, ModelRef)
    assert element.starts_cycle is True
    assert element.model is spec


def test_self_referential_optional_resolves_to_cycle() -> None:
    """A top-level `Optional["Self"]` resolves to a cycle-marked `ModelRef`.

    Pydantic resolves the string inside `Optional["Node"]` before
    `extract_model` runs -- the annotation's args are already
    `(<class Node>, NoneType)`, so no string reaches `_resolve_forward_ref`.
    This exercises the cycle guard through a Pydantic-resolved `Optional`,
    not the bare-string forward-ref path covered above.
    """

    class Node(BaseModel):
        val: int
        parent: Optional["Node"] = None

    spec = extract_model(Node)
    parent = next(f for f in spec.fields if f.name == "parent")

    assert isinstance(parent.shape, ModelRef)
    assert parent.shape.starts_cycle is True
    assert parent.shape.model is spec


def test_nested_list_forward_ref_resolves_to_cycle() -> None:
    """A `list[list["Self"]]` forward ref resolves through both array layers."""

    class Node(BaseModel):
        val: int
        grid: list[list["Node"]] = Field(default_factory=list)

    spec = extract_model(Node)
    grid = next(f for f in spec.fields if f.name == "grid")

    assert isinstance(grid.shape, ArrayOf)
    assert isinstance(grid.shape.element, ArrayOf)
    inner = grid.shape.element.element
    assert isinstance(inner, ModelRef)
    assert inner.starts_cycle is True


def test_extends_hoisted_into_field_metadata_is_not_a_constraint() -> None:
    """`Extends` must be excluded from the `FieldInfo.metadata` path too.

    Pydantic strips a top-level `Annotated` and hoists its metadata into
    `FieldInfo.metadata`, bypassing the Annotated-frame exclusion; without
    a filter in `attach_field_metadata`, the extension-target declaration
    would render as a constraint in generated docs.
    """

    class Place(BaseModel):
        name: str

    class Venue(BaseModel):
        capacity: Annotated[int, Field(ge=0), Extends(Place)]

    spec = extract_model(Venue)
    cap = next(f for f in spec.fields if f.name == "capacity")

    assert isinstance(cap.shape, Primitive)
    constraints = [cs.constraint for cs in cap.shape.constraints]
    assert any(isinstance(c, Ge) for c in constraints)
    assert not any(isinstance(c, Extends) for c in constraints)


def test_extends_in_rootmodel_root_metadata_is_not_a_constraint() -> None:
    """The `RootModel` root's hoisted metadata path excludes `Extends` too."""

    class Place(BaseModel):
        name: str

    class CapRoot(RootModel[Annotated[int, Field(ge=0), Extends(Place)]]):
        pass

    class Venue(BaseModel):
        capacity: CapRoot

    spec = extract_model(Venue)
    cap = next(f for f in spec.fields if f.name == "capacity")

    assert isinstance(cap.shape, Primitive)
    constraints = [cs.constraint for cs in cap.shape.constraints]
    assert any(isinstance(c, Ge) for c in constraints)
    assert not any(isinstance(c, Extends) for c in constraints)


def test_field_metadata_minlen_wrapped_as_array_min_len() -> None:
    """MinLen in field_info.metadata is wrapped to ArrayMinLen, not left as raw MinLen.

    Pydantic strips the outermost Annotated wrapper from non-optional,
    non-union list fields and moves MinLen to field_info.metadata. Without
    routing through attach_constraints, the raw MinLen would survive into
    the constraint table untyped, causing dispatch to raise TypeError at
    codegen time.
    """

    class M(BaseModel):
        items: list[str] = Field(min_length=2)

    spec = extract_model(M)
    items_field = next(f for f in spec.fields if f.name == "items")

    assert isinstance(items_field.shape, ArrayOf)
    constraints = [cs.constraint for cs in items_field.shape.constraints]
    assert ArrayMinLen(min_length=2) in constraints


def test_optional_discriminated_union_inside_annotated_extracts() -> None:
    """`Annotated[A | B | None, Field(discriminator=...)]` must extract.

    The `None` arm lives *inside* the `Annotated`, so no outer-optional
    stripping applies; the union-alias check must tolerate the vacuous arm.
    """

    class RideBase(BaseModel):
        pass

    class CarArm(RideBase):
        kind: Literal["car"] = "car"

    class BikeArm(RideBase):
        kind: Literal["bike"] = "bike"

    class Holder(BaseModel):
        ride: Annotated[CarArm | BikeArm | None, Field(discriminator="kind")] = None

    spec = extract_model(Holder)
    (ride,) = [f for f in spec.fields if f.name == "ride"]
    terminal = terminal_of(ride.shape)
    assert isinstance(terminal, UnionRef)
    assert terminal.union.discriminator_field == "kind"
    assert set(terminal.union.discriminator_mapping or {}) == {"car", "bike"}
    assert ride.is_optional


def test_direct_union_alias_field_keeps_discriminator() -> None:
    """A bare union-alias field must keep its discriminator.

    Pydantic hoists the discriminator onto `FieldInfo.discriminator` for a
    direct alias field, leaving a bare union in `field_info.annotation`.
    """

    class RideBase(BaseModel):
        pass

    class CarArm(RideBase):
        kind: Literal["car"] = "car"

    class BikeArm(RideBase):
        kind: Literal["bike"] = "bike"

    Ride = Annotated[CarArm | BikeArm, Field(discriminator="kind")]

    class Holder(BaseModel):
        ride: Ride

    spec = extract_model(Holder)
    (ride,) = [f for f in spec.fields if f.name == "ride"]
    terminal = terminal_of(ride.shape)
    assert isinstance(terminal, UnionRef)
    assert terminal.union.discriminator_field == "kind"
    assert set(terminal.union.discriminator_mapping or {}) == {"car", "bike"}
