"""Unit tests for the generic model extension mechanism.

These tests deliberately use local, non-Feature models to prove the mechanism is generic over any
pydantic `BaseModel`, not tied to Overture's `Feature` base class.
"""

import logging
from typing import Annotated, ForwardRef, Literal, NewType, Union, get_args

import pytest
from pydantic import BaseModel, Field, RootModel, ValidationError, computed_field

from overture.schema.system.extension import (
    _EXTENSION_ATTR,
    Extends,
    SelfReferentialRootError,
    applied_extension_names,
    create_extended_model,
    extends,
    extension_targets,
    wrap_extension,
)


class Target(BaseModel):
    name: str


class OtherTarget(BaseModel):
    label: str


class Unrelated(BaseModel):
    value: int


# ---------------------------------------------------------------------------
# Target validation
# ---------------------------------------------------------------------------


def test_extends_accepts_basemodel_targets() -> None:
    assert Extends(Target).extends == (Target,)
    assert Extends(Target, OtherTarget).extends == (Target, OtherTarget)


def test_extends_accepts_union_and_newtype_targets() -> None:
    Aliased = NewType("Aliased", Target)
    assert Extends(Target | OtherTarget).extends == (Target | OtherTarget,)
    assert Extends(Aliased).extends == (Aliased,)


def test_extends_rejects_non_model_targets() -> None:
    with pytest.raises(TypeError):
        Extends(int)
    with pytest.raises(TypeError):
        Extends("not a model")
    with pytest.raises(TypeError):
        Extends()  # at least one target required


def test_extends_rejects_partial_model_union() -> None:
    with pytest.raises(TypeError):
        Extends(Target | int)


def test_extends_rejects_rootmodel_with_non_model_root() -> None:
    class IntRoot(RootModel[int]):
        pass

    # A RootModel target is an alias over its root; a scalar root resolves to no
    # models, so there is nothing to extend.
    with pytest.raises(TypeError):
        Extends(IntRoot)
    with pytest.raises(TypeError):
        Extends(Target | IntRoot)


def test_extends_accepts_rootmodel_over_models() -> None:
    class Pair(RootModel[Target | OtherTarget]):
        pass

    # Alias semantics: a RootModel whose root resolves to models is a valid target.
    assert Extends(Pair).extends == (Pair,)


# ---------------------------------------------------------------------------
# extension_targets detection across declaration forms
# ---------------------------------------------------------------------------


def test_extension_targets_on_decorated_model() -> None:
    @extends(Target)
    class Ext(BaseModel):
        extra: str

    assert extension_targets(Ext) == (Target,)


def test_extension_targets_on_newtype_with_metadata() -> None:
    Scalar = NewType("Scalar", Annotated[int, Field(ge=0), Extends(Target)])
    assert extension_targets(Scalar) == (Target,)


def test_extension_targets_on_bare_annotated() -> None:
    bare = Annotated[int, Extends(Target, OtherTarget)]
    assert extension_targets(bare) == (Target, OtherTarget)


def test_extension_targets_returns_empty_for_non_extension() -> None:
    assert extension_targets(Target) == ()
    assert extension_targets(int) == ()
    assert extension_targets(Annotated[int, Field(ge=0)]) == ()


# ---------------------------------------------------------------------------
# wrap_extension
# ---------------------------------------------------------------------------


def test_wrap_extension_model_case() -> None:
    @extends(Target)
    class OpeningInfo(BaseModel):
        note: str

    wrapper = wrap_extension("opening_info", OpeningInfo)
    assert wrapper is not None
    assert wrapper.__name__ == "OpeningInfoExtension"
    assert set(wrapper.model_fields) == {"opening_info"}
    # Default is None and the original extension type is preserved for re-use.
    assert wrapper().model_dump()["opening_info"] is None
    assert getattr(wrapper, _EXTENSION_ATTR) is OpeningInfo
    # Targets remain introspectable through the wrapper.
    assert extension_targets(wrapper) == (Target,)
    # Validates an extension-only payload.
    validated = wrapper.model_validate({"opening_info": {"note": "hi"}})
    assert validated.model_dump()["opening_info"]["note"] == "hi"


def test_wrap_extension_scalar_case_preserves_constraints() -> None:
    Scalar = NewType("Scalar", Annotated[int, Field(ge=0, le=10), Extends(Target)])
    wrapper = wrap_extension("scalar_ext", Scalar)
    assert wrapper is not None
    assert wrapper.__name__ == "ScalarExtExtension"
    assert wrapper.model_validate({"scalar_ext": 5}).model_dump()["scalar_ext"] == 5
    # Field(ge/le) constraints survive the round-trip through the wrapper.
    with pytest.raises(ValidationError):
        wrapper.model_validate({"scalar_ext": 99})


def test_wrap_extension_returns_none_for_non_extension() -> None:
    assert wrap_extension("plain", Target) is None
    assert wrap_extension("plain", int) is None


@pytest.mark.parametrize(
    "name", ["_secret", "model_stuff", "not-an-identifier", "class", "copy"]
)
def test_wrap_extension_rejects_unsafe_field_names(name: str) -> None:
    @extends(Target)
    class Ext(BaseModel):
        note: str

    # Underscore names would silently become private attributes (a wrapper with no
    # field), `model_` names hit Pydantic's protected namespace, `BaseModel` attribute
    # names would shadow inherited behavior on every model, and the rest cannot be
    # referenced by generated code.
    with pytest.raises(ValueError, match="cannot be used as a field name"):
        wrap_extension(name, Ext)


# ---------------------------------------------------------------------------
# create_extended_model
# ---------------------------------------------------------------------------


def _wrap(name: str, obj: object) -> type[BaseModel]:
    wrapper = wrap_extension(name, obj)
    assert wrapper is not None
    return wrapper


def test_create_extended_model_adds_field_to_target() -> None:
    @extends(Target)
    class Ext(BaseModel):
        note: str

    extensions = {"ext": _wrap("ext", Ext)}
    extended = create_extended_model(Target, extensions)

    assert extended is not Target
    assert issubclass(extended, Target)
    assert "ext" in extended.model_fields
    # Field is optional with default None.
    assert extended(name="x").ext is None
    instance = extended(name="x", ext=Ext(note="hello"))
    assert instance.ext.note == "hello"


def test_create_extended_model_identity_for_non_matching_target() -> None:
    @extends(Target)
    class Ext(BaseModel):
        note: str

    extensions = {"ext": _wrap("ext", Ext)}
    # Unrelated is not a Target subclass — returned unchanged.
    assert create_extended_model(Unrelated, extensions) is Unrelated


def test_create_extended_model_double_application_is_noop() -> None:
    @extends(Target)
    class Ext(BaseModel):
        note: str

    extensions = {"ext": _wrap("ext", Ext)}
    once = create_extended_model(Target, extensions)
    twice = create_extended_model(once, extensions)
    # Already applied — no new subclass is created.
    assert twice is once


def test_create_extended_model_skips_field_name_collision() -> None:
    class HasName(BaseModel):
        name: str

    @extends(HasName)
    class Ext(BaseModel):
        note: str

    # Extension field name collides with an existing field on the target.
    extensions = {"name": _wrap("name", Ext)}
    assert create_extended_model(HasName, extensions) is HasName


def test_create_extended_model_no_collision_warning_for_non_target(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class HasNote(BaseModel):
        note: str

    @extends(Target)
    class Ext(BaseModel):
        x: int

    # HasNote shares a field name with the extension but is not one of its targets --
    # it must pass through silently, without a spurious collision warning.
    extensions = {"note": _wrap("note", Ext)}
    with caplog.at_level(logging.WARNING):
        assert create_extended_model(HasNote, extensions) is HasNote
    assert "collides" not in caplog.text


def test_create_extended_model_skips_alias_collision(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Aliased(BaseModel):
        internal: str = Field(alias="ext")

    @extends(Aliased)
    class Ext(BaseModel):
        x: int

    # The extension field name matches an existing field's payload-level alias.
    extensions = {"ext": _wrap("ext", Ext)}
    with caplog.at_level(logging.WARNING):
        assert create_extended_model(Aliased, extensions) is Aliased
    assert "collides" in caplog.text


def test_create_extended_model_skips_computed_field_collision() -> None:
    class WithComputed(BaseModel):
        first: str

        @computed_field  # type: ignore[prop-decorator]
        @property
        def ext(self) -> str:
            return self.first

    @extends(WithComputed)
    class Ext(BaseModel):
        x: int

    extensions = {"ext": _wrap("ext", Ext)}
    assert create_extended_model(WithComputed, extensions) is WithComputed


def test_create_extended_model_skips_computed_field_alias_collision() -> None:
    # A computed field's serialization alias occupies its payload key just as a
    # regular field alias does; applying an extension over it would produce
    # duplicate keys in `model_dump_json(by_alias=True)`.
    class WithAliasedComputed(BaseModel):
        first: str

        @computed_field(alias="ext")  # type: ignore[prop-decorator]
        @property
        def something(self) -> str:
            return self.first

    @extends(WithAliasedComputed)
    class Ext(BaseModel):
        x: int

    extensions = {"ext": _wrap("ext", Ext)}
    assert create_extended_model(WithAliasedComputed, extensions) is WithAliasedComputed


def test_create_extended_model_preserves_forward_ref_union_arms() -> None:
    # `X | Y` raises on arms that don't implement `|` (an unresolved
    # ForwardRef); the union rebuild must extend the model arms without
    # crashing on the unresolved ones.
    @extends(Target)
    class Ext(BaseModel):
        note: str

    extensions = {"ext": _wrap("ext", Ext)}
    alias = Union[Target, "NeverDefined"]  # type: ignore[name-defined] # noqa: F821

    extended = create_extended_model(alias, extensions)
    assert extended is not alias
    arms = get_args(extended)
    extended_target = next(
        a for a in arms if isinstance(a, type) and issubclass(a, Target)
    )
    assert "ext" in extended_target.model_fields
    assert any(isinstance(a, ForwardRef) for a in arms)


def test_create_extended_model_skips_class_attribute_collision() -> None:
    class WithMethod(BaseModel):
        first: str

        def ext(self) -> str:
            return self.first

    @extends(WithMethod)
    class Ext(BaseModel):
        x: int

    # `ext` is a method on the target; a field with that name would shadow it.
    extensions = {"ext": _wrap("ext", Ext)}
    assert create_extended_model(WithMethod, extensions) is WithMethod


def test_create_extended_model_leaves_scalar_rootmodel_unchanged() -> None:
    class IntRoot(RootModel[int]):
        pass

    @extends(Target)
    class Ext(BaseModel):
        x: int

    # A scalar root contains nothing to extend: the exact same class comes back, so
    # code constructing it via `root=` is untouched.
    extensions = {"ext": _wrap("ext", Ext)}
    assert create_extended_model(IntRoot, extensions) is IntRoot


def test_create_extended_model_rewrites_rootmodel_union_root() -> None:
    class Road(BaseModel):
        kind: Literal["road"] = "road"

    class Rail(BaseModel):
        kind: Literal["rail"] = "rail"

    class Segment(RootModel[Annotated[Road | Rail, Field(discriminator="kind")]]):
        def which(self) -> str:
            return self.root.kind

    @extends(Road)
    class Ext(BaseModel):
        note: str

    extensions = {"ext": _wrap("ext", Ext)}
    rebuilt = create_extended_model(Segment, extensions)

    # Rebuilt as a subclass: identity changes, construction and methods survive.
    assert rebuilt is not Segment
    assert issubclass(rebuilt, Segment)
    assert rebuilt.__name__ == Segment.__name__
    assert rebuilt.model_fields["root"].discriminator == "kind"
    # The targeted arm accepts extension data through the root; the other arm and
    # `root=` construction still work.
    v = rebuilt.model_validate({"kind": "road", "ext": {"note": "hi"}})
    assert v.which() == "road"
    assert v.root.ext.note == "hi"
    assert rebuilt(root=Rail()).which() == "rail"
    assert isinstance(rebuilt(root=Rail()), Segment)


def test_create_extended_model_rootmodel_identity_when_nothing_applies() -> None:
    class Pair(RootModel[Target | OtherTarget]):
        pass

    @extends(Unrelated)
    class Ext(BaseModel):
        x: int

    # No arm is targeted -- the exact same class comes back.
    extensions = {"ext": _wrap("ext", Ext)}
    assert create_extended_model(Pair, extensions) is Pair


def test_create_extended_model_rootmodel_double_application_is_noop() -> None:
    class Pair(RootModel[Target | OtherTarget]):
        pass

    @extends(Target)
    class Ext(BaseModel):
        x: int

    extensions = {"ext": _wrap("ext", Ext)}
    once = create_extended_model(Pair, extensions)
    assert once is not Pair
    twice = create_extended_model(once, extensions)
    assert twice is once


def test_create_extended_model_rootmodel_target_applies_to_arms() -> None:
    class Pair(RootModel[Target | OtherTarget]):
        pass

    # Alias semantics: targeting the RootModel targets its root's models, wherever
    # they appear -- including as individually registered entries.
    @extends(Pair)
    class Ext(BaseModel):
        x: int

    extensions = {"ext": _wrap("ext", Ext)}
    extended_target = create_extended_model(Target, extensions)
    assert extended_target is not Target
    assert "ext" in extended_target.model_fields
    assert create_extended_model(Unrelated, extensions) is Unrelated


def test_create_extended_model_self_referential_rootmodel_raises() -> None:
    class Loop(RootModel):  # type: ignore[type-arg]
        root: "Loop | Target"

    Loop.model_rebuild()

    @extends(Target)
    class Ext(BaseModel):
        x: int

    extensions = {"ext": _wrap("ext", Ext)}
    with pytest.raises(TypeError, match="self-referential"):
        create_extended_model(Loop, extensions)


def test_wrap_extension_accepts_rootmodel_extension() -> None:
    # An extension may itself be a RootModel: the wrapper field holds it and it
    # validates as its bare root value.
    @extends(Target)
    class Hours(RootModel[list[str]]):
        pass

    wrapper = _wrap("hours", Hours)
    validated = wrapper.model_validate({"hours": ["09:00-17:00"]})
    assert validated.model_dump()["hours"] == ["09:00-17:00"]
    extended = create_extended_model(Target, {"hours": wrapper})
    v = extended.model_validate({"name": "x", "hours": ["09:00-17:00"]})
    assert v.hours.root == ["09:00-17:00"]


def test_create_extended_model_recurses_into_union() -> None:
    @extends(Target)
    class Ext(BaseModel):
        note: str

    extensions = {"ext": _wrap("ext", Ext)}
    union = Target | Unrelated
    extended = create_extended_model(union, extensions)

    arms = {arm.__name__: arm for arm in get_args(extended)}
    # The Target arm gains the field; the Unrelated arm is untouched.
    assert "ext" in arms["Target"].model_fields  # type: ignore[union-attr]
    assert arms["Unrelated"] is Unrelated


def test_create_extended_model_recurses_into_newtype() -> None:
    @extends(Target)
    class Ext(BaseModel):
        note: str

    extensions = {"ext": _wrap("ext", Ext)}
    Aliased = NewType("Aliased", Target)
    extended = create_extended_model(Aliased, extensions)
    assert hasattr(extended, "__supertype__")
    assert "ext" in extended.__supertype__.model_fields


def test_create_extended_model_scalar_extension_field_type() -> None:
    Scalar = NewType("Scalar", Annotated[int, Field(ge=0, le=10), Extends(Target)])
    extensions = {"scalar": _wrap("scalar", Scalar)}
    extended = create_extended_model(Target, extensions)

    assert "scalar" in extended.model_fields
    assert extended(name="x", scalar=5).scalar == 5
    # The uint-like constraint carried by the NewType is enforced on the target.
    with pytest.raises(ValidationError):
        extended(name="x", scalar=99)


def test_standalone_wrapper_join_pattern() -> None:
    """The wrapper validates a standalone payload that joins onto an extended target."""

    @extends(Target)
    class Ext(BaseModel):
        note: str

    wrapper = _wrap("ext", Ext)
    extended = create_extended_model(Target, {"ext": wrapper})

    base = Target(name="x")
    ext_payload = wrapper.model_validate({"ext": {"note": "joined"}})
    joined = extended.model_validate(
        base.model_dump(exclude_unset=True) | ext_payload.model_dump(exclude_unset=True)
    )
    assert joined.name == "x"
    assert joined.ext.note == "joined"


class TestDuplicateDeclarationsMerge:
    def test_stacked_extends_decorators_merge_targets(self) -> None:
        @extends(OtherTarget)
        @extends(Target)
        class Both(BaseModel):
            note: str = ""

        # Bottom-up application: the inner (earlier) declaration comes first,
        # and neither is silently dropped.
        assert extension_targets(Both) == (Target, OtherTarget)

    def test_stacked_decorators_deduplicate(self) -> None:
        @extends(Target, OtherTarget)
        @extends(Target)
        class Dup(BaseModel):
            note: str = ""

        assert extension_targets(Dup) == (Target, OtherTarget)

    def test_subclass_declaration_shadows_inherited(self) -> None:
        @extends(Target)
        class Parent(BaseModel):
            note: str = ""

        @extends(OtherTarget)
        class Child(Parent):
            pass

        # A subclass speaks for itself; it does not merge with what it
        # inherits (which stays introspectable on the parent).
        assert extension_targets(Child) == (OtherTarget,)
        assert extension_targets(Parent) == (Target,)

    def test_multiple_extends_in_one_annotated_frame_merge(self) -> None:
        expr = Annotated[int, Extends(Target), Extends(OtherTarget), Extends(Target)]
        assert extension_targets(expr) == (Target, OtherTarget)

    def test_nested_annotated_flattens_and_merges(self) -> None:
        # typing flattens nested Annotated into one frame, inner metadata
        # first -- both declarations merge in declaration order.
        inner = Annotated[int, Extends(Target)]
        outer = Annotated[inner, Extends(OtherTarget)]
        assert extension_targets(outer) == (Target, OtherTarget)

    def test_nearest_frame_wins_over_deeper_frames(self) -> None:
        # A NewType boundary keeps frames distinct: the nearest frame that
        # declares any Extends decides, deeper frames are not consulted.
        inner_alias = NewType("inner_alias", Annotated[int, Extends(Target)])
        outer = Annotated[inner_alias, Extends(OtherTarget)]  # type: ignore[valid-type]
        assert extension_targets(outer) == (OtherTarget,)


class TestUnhashableTargets:
    def test_merge_deduplicates_by_equality_not_hash(self) -> None:
        # A valid target need not be hashable: Annotated[Model, []] resolves
        # to a model but carries unhashable metadata. Merging must not
        # require hashing.
        listy = Annotated[Target, []]

        @extends(listy, OtherTarget)  # type: ignore[arg-type]
        @extends(listy)  # type: ignore[arg-type]
        class Both(BaseModel):
            note: str = ""

        assert extension_targets(Both) == (listy, OtherTarget)

    def test_annotated_frame_merge_accepts_unhashable(self) -> None:
        listy = Annotated[Target, []]
        expr = Annotated[int, Extends(listy), Extends(OtherTarget), Extends(listy)]
        assert extension_targets(expr) == (listy, OtherTarget)


class TestWrapperModuleProvenance:
    def test_model_extension_keeps_its_defining_module(self) -> None:
        @extends(Target)
        class Modular(BaseModel):
            note: str = ""

        wrapper = wrap_extension("modular", Modular)
        assert wrapper is not None
        assert wrapper.__module__ == Modular.__module__

    def test_bare_annotated_uses_entry_point_module(self) -> None:
        # `Annotated[...]` reports typing's module, which says nothing about
        # where the extension was declared; the entry point's module does.
        expr = Annotated[int, Extends(Target)]
        wrapper = wrap_extension("cap", expr, module="my.extension.pkg")
        assert wrapper is not None
        assert wrapper.__module__ == "my.extension.pkg"

    def test_bare_annotated_without_module_falls_back(self) -> None:
        expr = Annotated[int, Extends(Target)]
        wrapper = wrap_extension("cap", expr)
        assert wrapper is not None
        assert wrapper.__module__ == "overture.schema.system.extension"


class TestContractHardening:
    def test_raw_extends_model_in_mapping_applies_as_itself(self) -> None:
        # A raw @extends model passed directly (instead of its wrap_extension
        # wrapper) is coherent: the model itself becomes the optional field's
        # type. Locked in so it degrades neither into an AttributeError nor a
        # silent no-op.
        @extends(Target)
        class RawExt(BaseModel):
            note: str

        extended = create_extended_model(Target, {"raw_ext": RawExt})
        assert isinstance(extended, type) and issubclass(extended, Target)
        annotation = extended.model_fields["raw_ext"].annotation
        assert annotation == (RawExt | None)

    def test_rebuilt_newtype_preserves_identity_metadata(self) -> None:
        @extends(Target)
        class Ext(BaseModel):
            note: str = ""

        wrapper = wrap_extension("cap", Ext)
        assert wrapper is not None
        Alias = NewType("Alias", Target)
        # A custom qualname distinguishes restoration from what a bare
        # NewType("Alias", ...) rebuild would stamp anyway.
        Alias.__qualname__ = "SomeNamespace.Alias"  # type: ignore[attr-defined]
        Alias.__doc__ = "An alias with prose."
        extended_alias = create_extended_model(Alias, {"cap": wrapper})
        assert extended_alias is not Alias
        assert extended_alias.__module__ == Alias.__module__
        assert extended_alias.__qualname__ == "SomeNamespace.Alias"
        assert extended_alias.__doc__ == "An alias with prose."

    def test_self_referential_root_raises_dedicated_error(self) -> None:
        class Loop(RootModel):  # type: ignore[type-arg]
            root: "Loop | Target"

        Loop.model_rebuild()

        @extends(Target)
        class Ext(BaseModel):
            x: int

        wrapper = wrap_extension("loop_ext", Ext)
        assert wrapper is not None
        with pytest.raises(SelfReferentialRootError):
            create_extended_model(Loop, {"loop_ext": wrapper})

    def test_applied_extension_names_tolerates_self_referential_root(self) -> None:
        # The aggregation helper feeds warning reporting, which must not
        # abort the extension pass on an entry that cannot have been extended.
        class Loop(RootModel):  # type: ignore[type-arg]
            root: "Loop | Target"

        Loop.model_rebuild()
        assert applied_extension_names(Loop) == frozenset()

    def test_applied_extension_names_propagates_unrelated_type_errors(self) -> None:
        # Only the self-referential root case is tolerated; any other
        # TypeError raised while inspecting the input must propagate.
        class Hostile:
            @property
            def __supertype__(self) -> object:
                raise TypeError("not a NewType")

        with pytest.raises(TypeError, match="not a NewType"):
            applied_extension_names(Hostile())


class TestRootModelDefaultFidelity:
    """Extending a RootModel must not change its root's requiredness."""

    def _wrapper(self) -> type[BaseModel]:
        @extends(Target)
        class Ext(BaseModel):
            note: str = ""

        wrapper = wrap_extension("fidelity_ext", Ext)
        assert wrapper is not None
        return wrapper

    def test_defaulted_root_stays_constructible(self) -> None:
        class DefaultedRoot(RootModel[Target]):
            root: Target = Target(name="d")

        extended = create_extended_model(
            DefaultedRoot, {"fidelity_ext": self._wrapper()}
        )
        assert extended is not DefaultedRoot
        assert extended.model_fields["root"].is_required() is False
        instance = extended()
        assert instance.root.name == "d"
        # The default is carried verbatim (defaults are not re-validated),
        # while explicit payloads validate against the extended root.
        validated = extended.model_validate(
            {"name": "x", "fidelity_ext": {"note": "n"}}
        )
        assert validated.root.fidelity_ext.note == "n"

    def test_default_factory_root_preserved(self) -> None:
        class FactoryRoot(RootModel[Target]):
            root: Target = Field(default_factory=lambda: Target(name="f"))

        extended = create_extended_model(FactoryRoot, {"fidelity_ext": self._wrapper()})
        assert extended is not FactoryRoot
        assert extended().root.name == "f"

    def test_required_root_stays_required(self) -> None:
        class RequiredRoot(RootModel[Target]):
            pass

        extended = create_extended_model(
            RequiredRoot, {"fidelity_ext": self._wrapper()}
        )
        assert extended is not RequiredRoot
        assert extended.model_fields["root"].is_required() is True
        with pytest.raises(ValidationError):
            extended()
