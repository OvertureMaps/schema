"""Question-shaped helpers over model-bearing type expressions.

A model-bearing type expression is any combination of `Annotated`, `Union`
(including `X | Y`), and `NewType` that resolves to Pydantic `BaseModel`
subclasses. One private walker (`_summarize_type_expression`) resolves an
expression; each public helper answers a single question about it, so
consumers never handle a rich summary object they mostly don't need:

- `model_types` / `non_model_parts` -- the concrete types it resolves to.
- `model_variants` -- model types plus the discriminator fields governing each.
- `is_model_union` -- is this a union of two or more models (and nothing else)?
- `resolves_to_models` -- does this resolve to models and nothing else?
- `union_discriminator` -- the outermost discriminator field name, if any.
- `root_annotated_metadata` -- `Annotated` metadata outside any multi-member union.
- `literal_values` / `single_literal_value` -- values of a (wrapped) `Literal`.
- `discriminator_values` -- normalized discriminator keys of a field annotation.
- `is_newtype` -- NewType detection across `typing` and `typing_extensions`.

`NoneType` and `Sentinel` union arms (`X | None`, `Omitable[X]`'s `MISSING`)
are *vacuous*: they express optionality/omissibility, not shape, so the walker
ignores them when deciding union-ness -- a union with exactly one non-vacuous
arm is treated as transparent, as if the union frame were not there. The
elided members still appear in `non_model_parts`, so strict callers keep
rejecting e.g. `Place | None` where a bare model is required. Note this
deliberately diverges from Pydantic's JSON-schema view, where `Optional[...]`
is an `anyOf` wrapper around the discriminated union rather than transparent.

The walker does not unwrap `Literal`, `list[...]`, or `dict[K, V]`, and
accumulates no field constraints -- field-level analysis is
`overture-schema-codegen`'s `analyze_type` (`extraction/type_analyzer.py`).
A `RootModel` subclass is an ordinary model type here, like any `BaseModel`; consumers
that treat a RootModel as an alias over its root (codegen extraction, the
extension mechanism) layer that unwrapping on top themselves.
"""

import types
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, ForwardRef, Literal, NewType, Union, get_args, get_origin

import typing_extensions
from pydantic import BaseModel, Discriminator, Tag
from pydantic.fields import FieldInfo
from typing_extensions import Sentinel


def resolve_discriminator_field_name(discriminator: object) -> str | None:
    """Resolve a Pydantic discriminator value to its field name string.

    Handles the three forms a discriminator can take:
    - A plain string (used directly as the field name).
    - A `pydantic.Discriminator` whose `.discriminator` attribute is a string.
    - A `pydantic.Discriminator` whose `.discriminator` is a callable
      produced by `Feature.field_discriminator`, which stores the field name
      as `_field_name` on the callable.

    Returns None if *discriminator* is None or its field name cannot be
    determined.
    """
    if discriminator is None:
        return None
    if isinstance(discriminator, str):
        return discriminator
    inner = getattr(discriminator, "discriminator", None)
    if isinstance(inner, str):
        return inner
    if callable(inner):
        field_name = getattr(inner, "_field_name", None)
        if isinstance(field_name, str):
            return field_name
    return None


def is_newtype(annotation: object) -> bool:
    """Whether *annotation* is a `NewType` -- `typing`'s or `typing_extensions`'s.

    `typing_extensions.NewType` is a distinct class from `typing.NewType` on
    Python 3.10/3.11, so a plain `isinstance(x, typing.NewType)` misses
    aliases created through it -- a form third-party schema packages
    legitimately use for cross-version compatibility.
    """
    return isinstance(annotation, (NewType, typing_extensions.NewType))


@dataclass(frozen=True, slots=True)
class ModelVariant:
    """One concrete model a type expression can resolve to."""

    model: type[BaseModel]
    # Resolved discriminator field names on the path from the root to this model,
    # outermost first (e.g. `("type", "subtype")` for a variant of a discriminated
    # union nested in another discriminated union).
    discriminator_path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _TypeExpressionSummary:
    """Result of one `_summarize_type_expression` walk; each public helper exposes one facet."""

    # Model variants in declaration order, without deduplication.
    variants: tuple[ModelVariant, ...]
    # Parts that are not `BaseModel` subclasses (e.g. `int` in `Place | int`),
    # excluding elided union members.
    non_model_parts: tuple[object, ...]
    # Elided union members: `NoneType` and `Sentinel` instances (e.g. `MISSING`)
    # -- they express optionality/omissibility, not shape.
    elided_union_members: tuple[object, ...]
    # Unevaluated `ForwardRef`s encountered during the walk. Each public helper
    # applies its own policy (raise / conservative False / ignore).
    unresolved_refs: tuple[ForwardRef, ...]
    # Field name of the outermost discriminator (`Field(discriminator=...)` or a bare
    # `pydantic.Discriminator`), resolved to a string.
    discriminator: str | None
    # Non-`Tag` `Annotated` metadata found outside any multi-arm union.
    metadata: tuple[object, ...]
    # True only for unions with two or more effective members; a union whose
    # elided members leave a single effective one is transparent.
    is_union: bool


def _summarize_type_expression(tp: object) -> _TypeExpressionSummary:
    """Walk a type expression, resolving it to its concrete model variants.

    Unwraps `Annotated[X, ...]`, `Union[X, Y]` (including `X | Y`), and `NewType`,
    recording along the way the discriminator field names from
    `Field(discriminator=...)` or bare `pydantic.Discriminator` metadata, plus the
    remaining root `Annotated` metadata.
    Lenient by design -- non-model parts are recorded in `non_model_parts`, and
    unevaluated `ForwardRef`s in `unresolved_refs`, never raised on during the
    walk, so each public helper applies its own policy: model accessors raise on
    unresolved refs (a partial model list would make models silently vanish),
    boolean predicates conservatively answer False, and optionality/metadata
    questions ignore them (an opaque ref cannot affect a *visible* `None` arm
    or root metadata).
    """
    variants: list[ModelVariant] = []
    non_model_parts: list[object] = []
    elided_union_members: list[object] = []
    unresolved_refs: list[ForwardRef] = []
    root_metadata: list[object] = []
    root_discriminator: str | None = None
    is_union = False

    def _visit(
        t: object,
        *,
        inside_multi_member_union: bool,
        discriminator_path: tuple[str, ...],
    ) -> None:
        nonlocal root_discriminator, is_union
        if isinstance(t, ForwardRef):
            if getattr(t, "__forward_evaluated__", False):
                _visit(
                    t.__forward_value__,
                    inside_multi_member_union=inside_multi_member_union,
                    discriminator_path=discriminator_path,
                )
                return
            unresolved_refs.append(t)
            return
        origin = get_origin(t)
        if origin is Annotated:
            inner, *metadata = get_args(t)
            effective_discriminator: str | None = None
            for meta in metadata:
                if isinstance(meta, Tag):
                    continue
                disc: object | None = None
                if isinstance(meta, FieldInfo) and meta.discriminator is not None:
                    disc = meta.discriminator
                elif isinstance(meta, Discriminator):
                    disc = meta
                if disc is not None:
                    # `Annotated` flattens inner metadata before outer metadata, and
                    # Pydantic lets the later/outer discriminator win.
                    effective_discriminator = resolve_discriminator_field_name(disc)
                if not inside_multi_member_union:
                    root_metadata.append(meta)
            if effective_discriminator is not None:
                discriminator_path = (*discriminator_path, effective_discriminator)
                # A discriminator inside a multi-member union belongs to that
                # member, not to the expression as a whole. Preserve the
                # outermost structural wrapper.
                if not inside_multi_member_union and root_discriminator is None:
                    root_discriminator = effective_discriminator
            _visit(
                inner,
                inside_multi_member_union=inside_multi_member_union,
                discriminator_path=discriminator_path,
            )
        elif origin is Union or origin is types.UnionType:
            effective_args: list[object] = []
            for arg in get_args(t):
                if arg is types.NoneType or isinstance(arg, Sentinel):
                    elided_union_members.append(arg)
                else:
                    effective_args.append(arg)
            if len(effective_args) == 1:
                # Elided members express optionality, not shape: a union they
                # leave with one effective member is transparent, as if the
                # union frame were not there.
                _visit(
                    effective_args[0],
                    inside_multi_member_union=inside_multi_member_union,
                    discriminator_path=discriminator_path,
                )
            else:
                is_union = True
                for arg in effective_args:
                    _visit(
                        arg,
                        inside_multi_member_union=True,
                        discriminator_path=discriminator_path,
                    )
        elif is_newtype(t):
            _visit(
                t.__supertype__,  # type: ignore[attr-defined]
                inside_multi_member_union=inside_multi_member_union,
                discriminator_path=discriminator_path,
            )
        elif isinstance(t, type) and issubclass(t, BaseModel):
            variants.append(
                ModelVariant(
                    model=t,
                    discriminator_path=discriminator_path,
                )
            )
        else:
            non_model_parts.append(t)

    _visit(tp, inside_multi_member_union=False, discriminator_path=())
    return _TypeExpressionSummary(
        variants=tuple(variants),
        non_model_parts=tuple(non_model_parts),
        elided_union_members=tuple(elided_union_members),
        unresolved_refs=tuple(unresolved_refs),
        discriminator=root_discriminator,
        metadata=tuple(root_metadata),
        is_union=is_union,
    )


def _raise_on_unresolved(summary: _TypeExpressionSummary) -> None:
    if summary.unresolved_refs:
        ref = summary.unresolved_refs[0]
        raise TypeError(
            f"Unevaluated forward reference {ref.__forward_arg__!r} in type "
            f"expression; resolve it (e.g. via `model_rebuild()`) first"
        )


def model_types(tp: object) -> tuple[type[BaseModel], ...]:
    """Return the concrete `BaseModel` classes a type expression resolves to.

    In declaration order, without deduplication. Empty when the expression
    contains no models. Raises `TypeError` on an unevaluated `ForwardRef`
    anywhere in the expression: a partial list would make the models behind
    unresolved references silently vanish.
    """
    summary = _summarize_type_expression(tp)
    _raise_on_unresolved(summary)
    return tuple(variant.model for variant in summary.variants)


def non_model_parts(tp: object) -> tuple[object, ...]:
    """Return the parts of a type expression that are not `BaseModel` subclasses.

    E.g. `(int,)` for `Place | int`, or the expression itself when it is not a
    type at all. Elided union members (`NoneType`, sentinels) are included, so
    a strict caller rejecting anything non-model keeps rejecting
    `Place | None`; use `resolves_to_models` where optionality should be
    tolerated. Unevaluated `ForwardRef`s are reported here too -- an
    unresolvable part is not a model. Empty means the expression resolves
    purely to models.
    """
    summary = _summarize_type_expression(tp)
    return (
        summary.non_model_parts
        + tuple(summary.unresolved_refs)
        + summary.elided_union_members
    )


def model_variants(tp: object) -> tuple[ModelVariant, ...]:
    """Return each concrete model of a type expression with the discriminator
    field names governing it.

    Use this instead of `model_types` when discriminator routing matters (e.g.
    mapping discriminator values to the variants of a nested discriminated
    union). Strict like `model_types`: raises on unevaluated `ForwardRef`s.
    """
    summary = _summarize_type_expression(tp)
    _raise_on_unresolved(summary)
    return summary.variants


def is_model_union(tp: object) -> bool:
    """Whether a type expression is a union of two or more `BaseModel` subclasses.

    Elided members are tolerated: `A | B | None` and `Omitable[A | B]` qualify.
    A union that elided members reduce to a single model (`A | None`) does not
    -- it is a plain (optional) model, not a union.
    """
    summary = _summarize_type_expression(tp)
    return (
        summary.is_union
        and len(summary.variants) >= 2
        and not summary.non_model_parts
        # Conservative: an expression that cannot be fully resolved is not
        # classified as a model union -- boolean classifiers must not raise.
        and not summary.unresolved_refs
    )


def resolves_to_models(tp: object) -> bool:
    """Whether a type expression resolves to one or more models and nothing else.

    Elided union members (`None`, sentinels) are tolerated -- a plain model,
    `A | B`, `A | None`, and `Omitable[A]` all qualify; `int`, `Model | int`,
    and expressions containing no model at all do not. Unlike
    `non_model_parts`, optionality is not held against the expression.
    """
    summary = _summarize_type_expression(tp)
    return (
        bool(summary.variants)
        and not summary.non_model_parts
        # Conservative: unresolved refs disqualify rather than raise.
        and not summary.unresolved_refs
    )


def accepts_none(tp: object) -> bool:
    """Whether a type expression accepts `None`, at any union nesting depth.

    `Annotated[A | None, ...] | B` accepts None just as `A | B | None` does --
    unions flatten at validation time, so a `None` member inside a nested arm
    makes the whole expression optional. Sentinel members do not count: they
    express omissibility, not None acceptance. Containers are not descended
    (`list[A | None]` is element-level nullability, not field optionality).
    Unresolved `ForwardRef`s are ignored: an opaque reference cannot affect
    whether a visible `None` arm is present.
    """
    summary = _summarize_type_expression(tp)
    return any(member is types.NoneType for member in summary.elided_union_members)


def union_discriminator(tp: object) -> str | None:
    """Return the field name of a type expression's outermost discriminator, if any.

    Recognizes both `Field(discriminator=...)` and bare `pydantic.Discriminator`
    metadata. A discriminator declared inside a multi-member union governs only
    its member and is not reported here (see `model_variants`); one inside a
    transparent optional frame (`Optional[Annotated[A | B, Field(...)]]`) is
    the expression's discriminator and *is* reported, even though Pydantic's
    JSON schema renders that form as an `anyOf` around the tagged union.
    """
    return _summarize_type_expression(tp).discriminator


def root_annotated_metadata(tp: object) -> tuple[object, ...]:
    """`Annotated` metadata of a type expression found outside any multi-member union.

    E.g. the discriminator `FieldInfo` of a discriminated-union alias, or a
    `Field(description=...)` documenting the alias -- including one inside a
    transparent optional frame. `pydantic.Tag` markers are excluded.
    """
    return _summarize_type_expression(tp).metadata


def literal_values(tp: object) -> tuple[object, ...] | None:
    """Return the values of a `Literal[...]` type expression, or None when not one.

    Recognizes field-level literal expressions only: `Annotated`, `NewType`,
    and transparent union frames (`Literal["x"] | None`) peel on the way, but
    containers deliberately do not -- callers pass arbitrary field annotations
    (`list[...]`, `dict[...]`), and those yield None rather than digging out
    element-level literals. Values are returned raw, so an `Enum` member comes
    back as the member, not its `.value`; garbage never raises.
    """
    while True:
        origin = get_origin(tp)
        if origin is Annotated:
            tp = get_args(tp)[0]
        elif origin is Union or origin is types.UnionType:
            effective_args = [
                arg
                for arg in get_args(tp)
                if arg is not types.NoneType and not isinstance(arg, Sentinel)
            ]
            if len(effective_args) != 1:
                return None
            tp = effective_args[0]
        elif is_newtype(tp):
            tp = tp.__supertype__  # type: ignore[attr-defined]
        else:
            break
    if get_origin(tp) is Literal:
        values: tuple[object, ...] = get_args(tp)
        return values
    return None


def single_literal_value(tp: object) -> object | None:
    """Return the sole value of a `Literal[...]` type expression, or None.

    `literal_values` with an exactly-one requirement: multi-value literals and
    non-literal expressions yield None. `Literal[None]` deliberately collapses
    to None as well -- callers use the result as a discriminator key or a
    name, where None is invalid anyway.
    """
    values = literal_values(tp)
    if values is not None and len(values) == 1:
        return values[0]
    return None


def discriminator_values(tp: object) -> tuple[str, ...] | None:
    """Return the normalized discriminator keys a field annotation accepts, or None.

    THE convention for discriminator keys, shared by codegen's discriminator
    mapping and the CLI's error routing: every `Literal` value, `Enum` members
    by their `.value`, and everything through `str()` (`Enum.value` is `Any`,
    so an int-valued enum must not smuggle a non-str key into mappings
    declared `dict[str, ...]`). Pydantic accepts multi-value literal tags --
    every value routes to the same member -- so all values are returned.
    None when the annotation has no literal values.
    """
    values = literal_values(tp)
    if values is None:
        return None
    return tuple(
        str(value.value) if isinstance(value, Enum) else str(value) for value in values
    )
