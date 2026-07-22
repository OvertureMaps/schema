"""Annotation-to-`FieldShape` analysis.

`analyze_type` recurses through a Python type annotation, peeling
`NewType`, `Annotated`, `Optional`, `list`, and `dict` layers one frame
at a time, and produces a `FieldShape` describing the structure with
constraints attached to the layer they target.

Forward references encountered along the way are resolved against the
`owner` model's namespace before classification. Builtin generics store
`list["Node"]`'s element as a bare `str` (not a `ForwardRef`), which
neither Pydantic nor `typing.get_type_hints` resolves; resolving it here
lets a self-referential field reach its model terminal so the cycle
guard in `extract_model` engages.

Each `Annotated` frame attaches its metadata to the shape its inner
annotation unwraps to, so that, e.g., the inner and outer `MinLen` in
`Annotated[list[Annotated[str, MinLen(2)]], MinLen(3)]` land on
different layers as different typed variants: `ArrayMinLen(3)` on the
`ArrayOf`, `ScalarMinLen(2)` on the `Primitive`.

MODEL and UNION terminals are resolved via optional callbacks. When
no resolver is supplied a MODEL terminal falls back to
`Primitive(source_type=cls)`; a multi-arm UNION raises
`UnsupportedUnionError`. Callers that need to recurse into sub-models
pass resolvers that build a `ModelRef`/`UnionRef` with the resolved
spec.

A `RootModel` never reaches those terminals: it serializes as its bare
root value, so it is unwrapped to the root type's shape (with any root
metadata reattached) before terminal classification -- resolver or not.
"""

from __future__ import annotations

import types
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import (
    Annotated,
    Any,
    ForwardRef,
    Literal,
    NoReturn,
    Union,
    get_args,
    get_origin,
)

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, RootModel
from pydantic.fields import FieldInfo
from typing_extensions import Sentinel, assert_never, evaluate_forward_ref

from .docstring import clean_docstring
from .field import (
    AnyScalar,
    ArrayOf,
    ConstraintSource,
    FieldShape,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    UnionRef,
)
from .field_walk import terminal_of
from .length_constraints import ArrayMaxLen, ArrayMinLen, ScalarMaxLen, ScalarMinLen
from .literal_alternatives import LiteralAlternatives


@dataclass(frozen=True, slots=True)
class _ContinueWith:
    """`_peel_union` result: next annotation to keep peeling.

    `literal_alternatives` carries the values of any `Literal[...]` arms
    dropped in favor of a single concrete arm, so the caller can attach a
    `LiteralAlternatives` constraint to the recursed shape.
    """

    annotation: object
    is_optional: bool
    literal_alternatives: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True)
class _Resolved:
    """`_peel_union` result: finished shape, short-circuit the unwrap."""

    shape: FieldShape
    is_optional: bool


@dataclass(frozen=True, slots=True)
class _NewTypeCtx:
    """The innermost NewType currently in scope."""

    name: str
    ref: object


__all__ = [
    "ConstraintSource",
    "ModelResolver",
    "UnionResolver",
    "UnresolvedForwardRefError",
    "UnsupportedUnionError",
    "analyze_type",
    "attach_constraints",
    "attach_field_metadata",
    "capture_union_members",
    "is_newtype",
    "single_literal_value",
    "unwrap_list",
]


class UnsupportedUnionError(TypeError):
    """Raised when `analyze_type` encounters a multi-type union it cannot represent."""


class UnresolvedForwardRefError(TypeError):
    """Raised when a forward-reference annotation cannot be resolved to a type.

    Subclasses `TypeError` so callers that already guard `analyze_type`
    with `except (TypeError, UnsupportedUnionError)` treat an unresolvable
    forward ref as the analyzable-shape failure it is.
    """


ModelResolver = Callable[[type[BaseModel]], FieldShape]
"""Resolver invoked when `analyze_type` reaches a `BaseModel` terminal."""

UnionResolver = Callable[[object, tuple[type[BaseModel], ...], str | None], FieldShape]
"""Resolver invoked at a multi-arm union terminal.

Receives the original union annotation, the tuple of member classes,
and the description accumulated from enclosing `Annotated` layers.
"""


def is_newtype(annotation: object) -> bool:
    """Check whether *annotation* is a `typing.NewType`.

    NewType creates a callable with a `__supertype__` attribute pointing
    to the wrapped type. No public API exists for this check.
    """
    return callable(annotation) and hasattr(annotation, "__supertype__")


class _UnionCaptured(Exception):  # noqa: N818 - control flow, not a true error
    """Raised by the capturing union resolver to short-circuit analyze_type."""

    def __init__(
        self, members: tuple[type[BaseModel], ...], description: str | None
    ) -> None:
        self.members = members
        self.description = description


def capture_union_members(
    annotation: object,
) -> tuple[tuple[type[BaseModel], ...], str | None] | None:
    """Peel wrappers from *annotation* and return its union members.

    Returns `(members, description)` when *annotation* (possibly wrapped
    in `Annotated`) terminates in a multi-arm union of `BaseModel`
    subclasses, otherwise `None`. Internally drives `analyze_type` with
    a capturing resolver and unwinds via an exception once the union
    terminal is reached. The resolver fires only after every enclosing
    `Annotated` layer is peeled, so the captured description matches what
    `analyze_type` would return.
    """

    def _capture(
        _ann: object,
        members: tuple[type[BaseModel], ...],
        description: str | None,
    ) -> NoReturn:
        raise _UnionCaptured(members, description)

    try:
        analyze_type(annotation, union_resolver=_capture)
    except _UnionCaptured as captured:
        return captured.members, captured.description
    except (TypeError, UnsupportedUnionError):
        return None
    return None


def _is_union(origin: object) -> bool:
    """Whether an origin represents a union type (`X | Y` or `Union[X, Y]`)."""
    return origin in (types.UnionType, Union)


def _filter_sentinel_arms(args: tuple[object, ...]) -> list[object]:
    """Remove `NoneType` and `Sentinel` arms from union type arguments."""
    return [a for a in args if a is not types.NoneType and not isinstance(a, Sentinel)]


def analyze_type(
    annotation: object,
    *,
    owner: type | None = None,
    model_resolver: ModelResolver | None = None,
    union_resolver: UnionResolver | None = None,
) -> tuple[FieldShape, bool, str | None]:
    """Analyze an annotation into a `FieldShape` plus field-level metadata.

    Parameters
    ----------
    annotation
        The annotation to analyze.
    owner
        The model class these annotations belong to. Supplies the
        namespace for resolving forward references (`list["Node"]`
        stores `"Node"` as a bare string). When None, an unresolvable
        forward ref raises `UnresolvedForwardRefError`.
    model_resolver
        Optional callback invoked when the terminal is a `BaseModel`
        subclass. Returns the `FieldShape` to use at that position --
        typically a `ModelRef` with a resolved `RecordSpec`. Defaults to
        a `Scalar` carrying the class as `source_type` for callers that
        cannot resolve sub-models (e.g. dict key/value analysis).
    union_resolver
        Optional callback invoked when the terminal is a multi-arm
        union of `BaseModel` subclasses. Returns the `FieldShape` to
        use -- typically a `UnionRef` with a resolved `UnionSpec`.
        Required to support unions; raises otherwise.

    Returns
    -------
    tuple[FieldShape, bool, str | None]
        The structural shape, whether the field accepts `None`, and
        the first `FieldInfo.description` encountered during unwrapping.
    """
    return _unwrap(
        annotation,
        newtype_ctx=None,
        owner=owner,
        model_resolver=model_resolver,
        union_resolver=union_resolver,
    )


def _unwrap(
    annotation: object,
    *,
    newtype_ctx: _NewTypeCtx | None,
    owner: type | None,
    model_resolver: ModelResolver | None,
    union_resolver: UnionResolver | None,
) -> tuple[FieldShape, bool, str | None]:
    """Recurse one annotation layer, returning its `FieldShape` subtree.

    Parameters
    ----------
    newtype_ctx
        The innermost `NewType` currently in scope, or None. Sets the
        terminal `Primitive.base_type` and tags constraints with their
        contributing `NewType`.
    owner
        The model class supplying the namespace for forward-ref
        resolution; invariant across the walk.

    Returns
    -------
    tuple
        The shape subtree, whether this layer or any descendant accepts
        `None`, and the first `FieldInfo.description` found.
    """

    def _recurse(
        annotation: object, newtype_ctx: _NewTypeCtx | None
    ) -> tuple[FieldShape, bool, str | None]:
        """Recurse into a child annotation, carrying the invariant resolvers."""
        return _unwrap(
            annotation,
            newtype_ctx=newtype_ctx,
            owner=owner,
            model_resolver=model_resolver,
            union_resolver=union_resolver,
        )

    if isinstance(annotation, (str, ForwardRef)):
        annotation = _resolve_forward_ref(annotation, owner)

    origin = get_origin(annotation)

    if is_newtype(annotation):
        ctx = _NewTypeCtx(annotation.__name__, annotation)  # type: ignore[attr-defined]
        inner, opt, desc = _recurse(annotation.__supertype__, ctx)  # type: ignore[attr-defined]
        inner = _erase_inner_newtypes(inner)
        return NewTypeShape(name=ctx.name, ref=ctx.ref, inner=inner), opt, desc

    if origin is Annotated:
        args = get_args(annotation)
        inner_annotation = args[0]
        own_desc: str | None = None
        collected: list[ConstraintSource] = []
        for c in args[1:]:
            if isinstance(c, FieldInfo):
                if c.description is not None and own_desc is None:
                    own_desc = clean_docstring(c.description)
                for m in c.metadata:
                    collected.append(_constraint_source(m, newtype_ctx))
            else:
                collected.append(_constraint_source(c, newtype_ctx))

        # Pick the annotation to recurse into and the optionality this
        # Annotated layer contributes. A directly-wrapped union is peeled
        # here so the resolver still sees the Annotated form; a `_Resolved`
        # union short-circuits with the constraints attached.
        next_annotation = inner_annotation
        layer_optional = False
        literal_alts: tuple[object, ...] = ()
        if _is_union(get_origin(inner_annotation)):
            result = _peel_union(
                inner_annotation,
                union_resolver,
                resolver_annotation=annotation,
                description=own_desc,
            )
            match result:
                case _Resolved(shape):
                    return (
                        attach_constraints(shape, tuple(collected)),
                        result.is_optional,
                        own_desc,
                    )
                case _ContinueWith(next_annotation, layer_optional, literal_alts):
                    pass
                case _:
                    assert_never(result)

        if literal_alts:
            collected.append(_literal_alternatives_source(literal_alts))
        inner, opt, desc = _recurse(next_annotation, newtype_ctx)
        inner = attach_constraints(inner, tuple(collected))
        return (
            inner,
            opt or layer_optional,
            own_desc if own_desc is not None else desc,
        )

    if _is_union(origin):
        result = _peel_union(annotation, union_resolver)
        match result:
            case _Resolved(shape):
                return shape, result.is_optional, None
            case _ContinueWith(next_annotation, is_optional, literal_alts):
                inner, opt, desc = _recurse(next_annotation, newtype_ctx)
                if literal_alts:
                    inner = attach_constraints(
                        inner, (_literal_alternatives_source(literal_alts),)
                    )
                return inner, opt or is_optional, desc
            case _:
                assert_never(result)

    if origin is list:
        args = get_args(annotation)
        if not args:
            raise TypeError("Bare list without type argument is not supported")
        element, _, desc = _recurse(args[0], newtype_ctx)
        # A list field is never optional on account of element nullability,
        # so the element's `is_optional` is dropped; its description is the
        # field's fallback prose when no field-level description exists.
        return ArrayOf(element=element, constraints=()), False, desc

    if origin is dict:
        args = get_args(annotation)
        if not args:
            raise TypeError("Bare dict without type arguments is not supported")
        key_shape, _, _ = _recurse(args[0], None)
        value_shape, _, _ = _recurse(args[1], None)
        return MapOf(key=key_shape, value=value_shape, constraints=()), False, None

    if isinstance(annotation, type) and issubclass(annotation, RootModel):
        # A RootModel serializes as its bare root value, so unwrap to the
        # root type's shape. Root-level constraints reattach exactly as
        # field metadata does, so a constrained root
        # (`RootModel[Annotated[list, MaxLen]]`) keeps its length-wrapped
        # variant on the unwrapped layer.
        root = annotation.model_fields["root"]
        inner, opt, desc = _recurse(root.annotation, newtype_ctx)
        return attach_field_metadata(inner, root), opt, desc

    return _terminal(annotation, newtype_ctx, model_resolver), False, None


def _resolve_forward_ref(annotation: str | ForwardRef, owner: type | None) -> object:
    """Resolve a string / `ForwardRef` annotation to its type object.

    Resolves against *owner*'s module and class namespaces, plus *owner*
    bound to its own name. The class namespace lets a forward ref to a
    nested model (`Outer.Inner`) resolve; the self-name binding lets a
    self-referential model defined in a local scope (e.g. a test body)
    resolve `"Owner"` even when it is absent from the module globals.
    Raises `UnresolvedForwardRefError` for a name not in scope
    (`NameError`), a missing attribute on a dotted reference
    (`AttributeError`), or a string that is not a valid type expression
    (`SyntaxError`) -- a clean, named failure in place of the opaque
    `TypeError` the terminal classifier would otherwise raise on a bare
    string.
    """
    if owner is not None:
        localns = {**vars(owner), owner.__name__: owner}
    else:
        localns = None
    try:
        ref = ForwardRef(annotation) if isinstance(annotation, str) else annotation
        return evaluate_forward_ref(ref, owner=owner, locals=localns)
    except (NameError, SyntaxError, AttributeError) as exc:
        target = (
            annotation if isinstance(annotation, str) else annotation.__forward_arg__
        )
        context = f" while extracting {owner.__qualname__}" if owner is not None else ""
        raise UnresolvedForwardRefError(
            f"Cannot resolve forward reference {target!r}{context}"
        ) from exc


def _constraint_source(
    constraint: object, newtype_ctx: _NewTypeCtx | None
) -> ConstraintSource:
    return ConstraintSource(
        source_ref=newtype_ctx.ref if newtype_ctx else None,
        source_name=newtype_ctx.name if newtype_ctx else None,
        constraint=constraint,
    )


def _literal_alternatives_source(values: tuple[object, ...]) -> ConstraintSource:
    """Wrap dropped union `Literal` values as a `LiteralAlternatives` source."""
    return ConstraintSource(
        source_ref=None, source_name=None, constraint=LiteralAlternatives(values)
    )


def _erase_inner_newtypes(shape: FieldShape) -> FieldShape:
    """Drop every `NewTypeShape` reachable through `ArrayOf` layers.

    A `NewType` chain — including NewTypes nested as list elements —
    collapses to a single `NewTypeShape` (the outermost), with inner
    NewType names surviving only as the terminal `Primitive.base_type`.
    Each `NewType` frame calls this on its recursion result so that by
    the time the outermost frame returns, exactly one `NewTypeShape`
    remains per spine.

    Recurses through `ArrayOf.element` but stops at `MapOf` — `dict`
    key/value are independent spines, each keeping its own outermost
    `NewTypeShape` — and at scalar / `ModelRef` / `UnionRef` terminals.
    """
    match shape:
        case NewTypeShape(inner=inner):
            return _erase_inner_newtypes(inner)
        case ArrayOf(element=element):
            return replace(shape, element=_erase_inner_newtypes(element))
        case _:
            return shape


def attach_constraints(
    shape: FieldShape, constraints: tuple[ConstraintSource, ...]
) -> FieldShape:
    """Prepend `constraints` to the outermost non-`NewTypeShape` layer.

    Skips any number of leading `NewTypeShape` wrappers, then prepends
    to the `.constraints` of the first `ArrayOf`, `MapOf`, `Primitive`,
    `LiteralScalar`, or `AnyScalar` reached. Does not descend into
    `ArrayOf.element` or `MapOf.key` / `.value`. `ModelRef` / `UnionRef`
    carry no constraints, so a constraint destined for a model/union
    terminal (`Annotated[SomeModel, SomeConstraint()]`) raises
    `NotImplementedError` rather than vanishing from both docs and
    validation -- no current schema field does this, and silently
    dropping it would diverge the generated output from the source.

    Length constraints (`annotated_types.MinLen` / `MaxLen`) are wrapped
    into the typed `length_constraints` variants matching the
    attachment layer: `ArrayMinLen` / `ArrayMaxLen` on `ArrayOf`,
    `ScalarMinLen` / `ScalarMaxLen` on scalar layers. `MapOf` raises:
    map-length constraints have no current schema use and would
    otherwise silently take the scalar path.
    """
    if not constraints:
        return shape
    match shape:
        case NewTypeShape(inner=inner):
            return replace(shape, inner=attach_constraints(inner, constraints))
        case ArrayOf():
            wrapped = tuple(_wrap_length_for_array(cs) for cs in constraints)
            return replace(shape, constraints=wrapped + shape.constraints)
        case MapOf():
            _reject_length_on_map(constraints)
            return replace(shape, constraints=constraints + shape.constraints)
        case Primitive() | LiteralScalar() | AnyScalar():
            wrapped = tuple(_wrap_length_for_scalar(cs) for cs in constraints)
            return replace(shape, constraints=wrapped + shape.constraints)
        case ModelRef() | UnionRef():
            names = ", ".join(type(cs.constraint).__name__ for cs in constraints)
            raise NotImplementedError(
                f"Constraints ({names}) on a model/union terminal are not "
                f"supported; attach them to a scalar or array layer instead"
            )
        case _:
            assert_never(shape)


def attach_field_metadata(shape: FieldShape, field_info: FieldInfo) -> FieldShape:
    """Merge constraints from `field_info.metadata` onto *shape*.

    Routes the metadata through `attach_constraints` so length-constraint
    wrapping applies here just as it does during normal annotation
    unwrapping: the constraints anchor at the topmost constraint-bearing
    layer. Returns *shape* unchanged when there is no metadata.
    """
    if not field_info.metadata:
        return shape
    extra = tuple(ConstraintSource(None, None, m) for m in field_info.metadata)
    return attach_constraints(shape, extra)


def _wrap_length_for_array(cs: ConstraintSource) -> ConstraintSource:
    """Replace a raw `MinLen`/`MaxLen` with its `ArrayOf`-layer variant.

    Uses exact-type checks so already-wrapped variants (`ArrayMinLen`,
    `ScalarMinLen`, etc.) are returned unchanged.
    """
    if type(cs.constraint) is MinLen:
        return replace(cs, constraint=ArrayMinLen(min_length=cs.constraint.min_length))
    if type(cs.constraint) is MaxLen:
        return replace(cs, constraint=ArrayMaxLen(max_length=cs.constraint.max_length))
    return cs


def _wrap_length_for_scalar(cs: ConstraintSource) -> ConstraintSource:
    """Replace a raw `MinLen`/`MaxLen` with its scalar-layer variant.

    Uses exact-type checks so already-wrapped variants (`ArrayMinLen`,
    `ScalarMinLen`, etc.) are returned unchanged.
    """
    if type(cs.constraint) is MinLen:
        return replace(cs, constraint=ScalarMinLen(min_length=cs.constraint.min_length))
    if type(cs.constraint) is MaxLen:
        return replace(cs, constraint=ScalarMaxLen(max_length=cs.constraint.max_length))
    return cs


def _reject_length_on_map(constraints: tuple[ConstraintSource, ...]) -> None:
    """Raise on `MinLen`/`MaxLen` attached to a `MapOf` layer."""
    for cs in constraints:
        if isinstance(cs.constraint, (MinLen, MaxLen)):
            raise NotImplementedError(
                f"{type(cs.constraint).__name__} on a Map type is not supported"
            )


def _terminal(
    annotation: object,
    newtype_ctx: _NewTypeCtx | None,
    model_resolver: ModelResolver | None,
) -> FieldShape:
    """Classify a fully-unwrapped terminal annotation into a shape."""
    if annotation is Any:
        return AnyScalar(constraints=())
    if get_origin(annotation) is Literal:
        return LiteralScalar(values=tuple(get_args(annotation)), constraints=())
    if not isinstance(annotation, type):
        raise TypeError(f"Unsupported annotation type: {type(annotation)}")
    if issubclass(annotation, list):
        raise TypeError("Bare list without type argument is not supported")
    if issubclass(annotation, dict):
        raise TypeError("Bare dict without type arguments is not supported")
    if issubclass(annotation, BaseModel) and model_resolver is not None:
        return model_resolver(annotation)
    base_type = newtype_ctx.name if newtype_ctx else annotation.__name__
    return Primitive(base_type=base_type, source_type=annotation, constraints=())


def _peel_union(
    annotation: object,
    union_resolver: UnionResolver | None,
    *,
    resolver_annotation: object | None = None,
    description: str | None = None,
) -> _ContinueWith | _Resolved:
    """Process one union layer.

    Filters out `None` / `Sentinel` arms (recording `is_optional`), then
    drops `Literal[...]` arms when a concrete (non-Literal) arm exists.
    A single remaining arm is returned as `_ContinueWith`; multiple arms
    invoke `union_resolver` and the result is returned as `_Resolved`
    (raising `UnsupportedUnionError` when no resolver is supplied).

    `resolver_annotation` is passed to `union_resolver` instead of
    `annotation` when set. This lets the `Annotated` branch forward the
    full `Annotated[X | Y, ...]` form so resolvers can recover
    discriminator metadata that the `Annotated` peeling step consumed.
    """
    args = get_args(annotation)
    is_optional = any(a is types.NoneType for a in args)

    non_none_args = _filter_sentinel_arms(args)
    concrete_args = [a for a in non_none_args if get_origin(a) is not Literal]
    real_args = concrete_args if concrete_args else non_none_args

    # A single concrete arm alongside `Literal[...]` arms keeps the concrete arm
    # as the shape; the literal values ride along as a LiteralAlternatives
    # constraint so they bypass the concrete arm's checks. Multi-arm and
    # no-concrete-arm unions are unchanged (the literals stay dropped).
    literal_alternatives: tuple[object, ...] = ()
    if len(concrete_args) == 1:
        literal_args = [a for a in non_none_args if get_origin(a) is Literal]
        literal_alternatives = tuple(v for a in literal_args for v in get_args(a))

    if len(real_args) > 1:
        members: list[type[BaseModel]] = []
        for arg in real_args:
            inner = arg
            if get_origin(inner) is Annotated:
                inner = get_args(inner)[0]
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                members.append(inner)
            else:
                raise UnsupportedUnionError(
                    f"Multi-type unions not supported: {annotation}"
                )
        if union_resolver is None:
            raise UnsupportedUnionError(
                f"No union_resolver supplied for multi-arm union: {annotation}"
            )
        return _Resolved(
            union_resolver(
                resolver_annotation or annotation, tuple(members), description
            ),
            is_optional,
        )

    if not real_args:
        raise UnsupportedUnionError(f"Union with no concrete types: {annotation}")

    return _ContinueWith(real_args[0], is_optional, literal_alternatives)


def unwrap_list(annotation: object) -> object:
    """Strip `| None`, `Sentinel`, and outermost `list[]` wrappers."""
    if _is_union(get_origin(annotation)):
        args = _filter_sentinel_arms(get_args(annotation))
        if len(args) == 1:
            annotation = args[0]

    while get_origin(annotation) is list:
        annotation = get_args(annotation)[0]
    return annotation


def single_literal_value(annotation: object) -> object | None:
    """Extract a single literal value from a type annotation, or `None`.

    Returns `None` for multi-value Literals -- callers needing all
    values should use `analyze_type` and inspect the terminal
    `LiteralScalar`'s `values`.
    """
    try:
        shape, _, _ = analyze_type(annotation)
    except (TypeError, UnsupportedUnionError):
        return None
    terminal = terminal_of(shape)
    if isinstance(terminal, LiteralScalar) and len(terminal.values) == 1:
        return terminal.values[0]
    return None
