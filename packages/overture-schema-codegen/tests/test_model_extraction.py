"""Tests for `extract_model`."""

from collections.abc import Callable
from typing import Annotated, Optional

import pytest
from codegen_test_support import FeatureWithRootModel
from pydantic import MISSING, BaseModel, Field
from typing_extensions import deprecated

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
from overture.schema.codegen.extraction.specs import UNDEFINED
from overture.schema.common.scoping import Scope, scoped
from overture.schema.common.scoping.vehicle import VehicleSelector
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.optionality import Omitable


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
        children: list["Node"]

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
        grid: list[list["Node"]]

    spec = extract_model(Node)
    grid = next(f for f in spec.fields if f.name == "grid")

    assert isinstance(grid.shape, ArrayOf)
    assert isinstance(grid.shape.element, ArrayOf)
    inner = grid.shape.element.element
    assert isinstance(inner, ModelRef)
    assert inner.starts_cycle is True


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


def test_field_with_no_default_carries_undefined() -> None:
    """A field with no declared default reports `UNDEFINED`, not `None`.

    `None` is a legal declared default (see below); collapsing "no
    default" into `None` would make the two indistinguishable to a
    consumer trying to warn on declared defaults.
    """

    class M(BaseModel):
        name: str

    spec = extract_model(M)
    name_field = next(f for f in spec.fields if f.name == "name")

    assert name_field.default is UNDEFINED


def test_field_with_non_none_default_carries_declared_value() -> None:
    """A field with a plain non-None default carries that value on the spec."""

    class M(BaseModel):
        count: int = 3

    spec = extract_model(M)
    count_field = next(f for f in spec.fields if f.name == "count")

    assert count_field.default == 3


def test_field_with_none_default_is_distinguished_from_no_default() -> None:
    """A field whose declared default IS `None` must not read as "no default".

    This is the load-bearing case: `field_info.default` is `None` here,
    not `UNDEFINED`, so a consumer can tell "declares a default
    of None" apart from "declares no default at all".
    """

    class M(BaseModel):
        note: str | None = None

    spec = extract_model(M)
    note_field = next(f for f in spec.fields if f.name == "note")

    assert note_field.default is None
    assert note_field.default is not UNDEFINED


def test_default_factory_is_refused_by_name() -> None:
    """A `default_factory` field is refused, naming the model and field.

    A factory is a Python callable. No target this IR feeds can render
    one -- not Markdown, not a PySpark expression, not JSON Schema -- and
    invoking it at extraction would freeze one sample of a value meant to
    be produced per instance. Carrying it as "no default" instead hides a
    declared default from anything reading the IR, so extraction refuses
    it where the author can still see which field is at fault.
    """

    class M(BaseModel):
        children: list[str] = Field(default_factory=list)

    with pytest.raises(TypeError, match=r"M\.children.*default_factory"):
        extract_model(M)


def test_omitable_field_reports_no_default_not_the_missing_sentinel() -> None:
    """`Omitable[T]` must not read as declaring a default.

    `Omitable[T]` is `Field(default=MISSING)` -- machinery for "this key may
    be absent", chosen to get JSON Schema omissibility instead of Pydantic
    nullability. `MISSING` is not a value anyone declared, so carrying it
    through would make every `Omitable` field claim a default it does not
    have. The carrier exists so a consumer can warn on declared defaults, and
    `Feature.bbox` and `Feature.id` are both `Omitable`, so every feature model
    in the schema inherits two of them -- each one a false warning.

    The over-reach direction -- normalizing away a genuine default too -- is
    covered by `test_field_with_none_default_is_distinguished_from_no_default`,
    confirmed by mutation: replacing the body with an unconditional
    `return UNDEFINED` fails that test.
    """

    class M(BaseModel):
        maybe: Omitable[int]

    spec = extract_model(M)
    maybe_field = next(f for f in spec.fields if f.name == "maybe")

    assert maybe_field.default is UNDEFINED
    assert maybe_field.default is not MISSING


def test_field_deprecated_with_message_carries_flag_and_message() -> None:
    """`Field(deprecated="...")` sets both `is_deprecated` and the message."""

    class M(BaseModel):
        old: str | None = Field(default=None, deprecated="Use `new` instead.")

    spec = extract_model(M)
    old = next(f for f in spec.fields if f.name == "old")

    assert old.is_deprecated is True
    assert old.deprecation_message == "Use `new` instead."


def test_field_deprecated_bare_true_carries_flag_with_no_message() -> None:
    """A bare `deprecated=True` sets the flag but leaves the message `None`.

    The control on the message test above: without this, a field that
    declares no message at all could not be told apart from one that does.
    """

    class M(BaseModel):
        old: str | None = Field(default=None, deprecated=True)

    spec = extract_model(M)
    old = next(f for f in spec.fields if f.name == "old")

    assert old.is_deprecated is True
    assert old.deprecation_message is None


@pytest.mark.parametrize("deprecated_value", ["", "   ", "\n"])
def test_field_deprecated_blank_message_extracts_like_bare_true(
    deprecated_value: str,
) -> None:
    """A blank message is no message: it extracts exactly as `deprecated=True`.

    Otherwise `""` would key apart from `True` in a union, splitting two rows
    that render identically, and `"   "` would render an empty note.
    """

    class M(BaseModel):
        old: str | None = Field(default=None, deprecated=deprecated_value)

    old = next(f for f in extract_model(M).fields if f.name == "old")

    assert old.is_deprecated is True
    assert old.deprecation_message is None


def test_field_deprecated_via_annotated_marker_carries_the_message() -> None:
    """The PEP 702 marker used directly as `Annotated` metadata also carries.

    `deprecated(...)` is usable both inside `Field(deprecated=...)` and
    directly as `Annotated` metadata; Pydantic surfaces the marker object
    itself (not a plain string) on `field_info.deprecated` for this form, so
    its `.message` has to be unwrapped rather than read as a string.
    """

    class M(BaseModel):
        old: Annotated[str, deprecated("Use `new` instead.")] = "x"

    spec = extract_model(M)
    old = next(f for f in spec.fields if f.name == "old")

    assert old.is_deprecated is True
    assert old.deprecation_message == "Use `new` instead."


def test_field_not_deprecated_by_default() -> None:
    """A field that never declares `deprecated` extracts as not deprecated.

    A stray `is_deprecated=True` default on `FieldSpec` would satisfy the
    two tests above; this one would fail.
    """

    class M(BaseModel):
        current: str = "x"

    spec = extract_model(M)
    current = next(f for f in spec.fields if f.name == "current")

    assert current.is_deprecated is False
    assert current.deprecation_message is None


def test_model_deprecated_via_pep_702_carries_the_message() -> None:
    """A class decorated with `@deprecated(...)` carries its message on the spec.

    `typing_extensions.deprecated` (PEP 702) sets `__deprecated__` on the
    decorated class.
    """

    @deprecated("Use `NewFeature` instead.")
    class OldFeature(BaseModel):
        name: str

    spec = extract_model(OldFeature)

    assert spec.deprecated == "Use `NewFeature` instead."


def test_model_deprecation_does_not_inherit_to_subclasses() -> None:
    """A subclass of a deprecated model is not itself deprecated.

    `__deprecated__` is a plain class attribute, so ordinary attribute
    lookup finds it through the MRO. Reading it that way would mark every
    subclass of a deprecated model deprecated and render a banner on a
    feature page that never declared one. `TransportationSegment` and
    `VehicleSelectorBase` both have subclasses in the published schema.
    """

    @deprecated("Use `NewFeature` instead.")
    class OldFeature(BaseModel):
        name: str

    # Subclassing a deprecated class is itself what PEP 702 warns about.
    with pytest.warns(DeprecationWarning):

        class CurrentFeature(OldFeature):
            pass

    assert getattr(CurrentFeature, "__deprecated__", None) is not None
    assert extract_model(CurrentFeature).deprecated is None
    assert extract_model(OldFeature).deprecated == "Use `NewFeature` instead."


@pytest.mark.parametrize(
    "decorator",
    [no_extra_fields, scoped(Scope.HEADING)],
    ids=["no_extra_fields", "scoped"],
)
def test_model_deprecation_survives_a_decorator_applied_over_it(
    decorator: Callable[[type[BaseModel]], type[BaseModel]],
) -> None:
    """A decorator applied over `@deprecated` keeps the model deprecated.

    Model-constraint decorators and `@scoped` return a new subclass of the
    class they decorate. That subclass is the class the module exports, so
    the deprecation the author declared has to be declared on it too.
    """

    @decorator
    @deprecated("Use `NewFeature` instead.")
    class OldFeature(BaseModel):
        name: str

    assert extract_model(OldFeature).deprecated == "Use `NewFeature` instead."


def test_model_not_deprecated_by_default() -> None:
    """A model with no `@deprecated` decorator extracts with `deprecated=None`.

    The control on the test above: without it, a stray non-`None` default
    on `RecordSpec.deprecated` would satisfy it trivially.
    """

    class CurrentFeature(BaseModel):
        name: str

    spec = extract_model(CurrentFeature)

    assert spec.deprecated is None
