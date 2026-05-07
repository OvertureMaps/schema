"""Format `FieldShape` trees as markdown type strings with cross-page links."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from pydantic import BaseModel

from ..extraction.field import (
    AnyScalar,
    ArrayOf,
    FieldShape,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    Scalar,
    UnionRef,
)
from ..extraction.specs import FieldSpec, TypeIdentity, is_pydantic_sourced
from ..extraction.type_registry import (
    get_type_mapping,
    is_semantic_newtype,
    resolve_type_name,
)
from .link_computation import LinkContext

__all__ = [
    "format_type",
    "format_underlying_type",
    "resolve_type_link",
]


def _code_link(name: str, href: str) -> str:
    """Format a markdown link with inline-code text: `[``name``](href)`."""
    return f"[`{name}`]({href})"


def resolve_type_link(identity: TypeIdentity, ctx: LinkContext | None = None) -> str:
    """Resolve a `TypeIdentity` to a linked or plain code span.

    With `ctx`, links only to types in the registry (types without
    pages render as inline code). Without context, renders as inline
    code -- producing a link requires a placement registry to compute
    correct relative paths.
    """
    if ctx:
        href = ctx.resolve_link(identity)
        if href:
            return _code_link(identity.name, href)
    return f"`{identity.name}`"


def _wrap_list_n(inner: str, depth: int) -> str:
    """Wrap an inner type string in `list<...>` markdown syntax *depth* times.

    Builds a single broken-backtick wrapper rather than nesting
    iteratively, since iterative nesting creates adjacent backticks
    that CommonMark interprets as multi-backtick code span delimiters.
    """
    return f"`{'list<' * depth}`{inner}`{'>' * depth}`"


def _plain_list_type(base: str, depth: int) -> str:
    """Format a plain (unlinked) list type string for *depth* nesting levels."""
    return f"`{'list<' * depth}{base}{'>' * depth}`"


def _peel_arrays(shape: FieldShape) -> tuple[int, FieldShape]:
    """Strip outer `ArrayOf` layers; return (count, inner)."""
    depth = 0
    while isinstance(shape, ArrayOf):
        depth += 1
        shape = shape.element
    return depth, shape


def _format_literal(values: tuple[object, ...]) -> str:
    """Format Literal values for display."""
    if len(values) == 1:
        return f'`"{values[0]}"`'
    return r" \| ".join(f'`"{v}"`' for v in values)


def _format_union_members(
    members: Sequence[type[BaseModel]],
    ctx: LinkContext | None,
    separator: str = r" \| ",
) -> str:
    r"""Format union members as individually linked / backticked names.

    Each member is resolved independently so members with pages get
    linked while others render as plain code spans. `separator` is
    inserted between members (default is `\|` for table-cell safety).
    """
    return separator.join(resolve_type_link(TypeIdentity.of(m), ctx) for m in members)


def _model_link(model_ref: ModelRef, ctx: LinkContext | None) -> str:
    """Resolve a `ModelRef` to a markdown link or fallback code span."""
    src = model_ref.model.source_type
    if src is not None:
        return resolve_type_link(TypeIdentity(src, model_ref.model.name), ctx)
    return f"`{model_ref.model.name}`"


def _scalar_identity(scalar: Primitive) -> TypeIdentity | None:
    """Return a linkable identity for a `Primitive`'s `source_type`, if any."""
    src = scalar.source_type
    if src is None:
        return None
    if isinstance(src, type) and (
        issubclass(src, Enum) or issubclass(src, BaseModel) or is_pydantic_sourced(src)
    ):
        return TypeIdentity.of(src)
    return None


def _scalar_display(scalar: Scalar, ctx: LinkContext | None) -> tuple[str, bool]:
    """Render a `Scalar` variant as a markdown string; second value is True if linked.

    Linked when the scalar is a `Primitive` with an Enum / BaseModel /
    Pydantic-sourced `source_type` whose identity resolves to a page.
    Otherwise renders as the registry-resolved markdown name.
    """
    if isinstance(scalar, Primitive):
        identity = _scalar_identity(scalar)
        if identity is not None and ctx:
            href = ctx.resolve_link(identity)
            if href:
                return _code_link(identity.name, href), True
        if identity is not None:
            return f"`{identity.name}`", False
    return f"`{_registry_name(scalar)}`", False


def _registry_name(scalar: Scalar) -> str:
    """Resolve a scalar to its markdown registry name (e.g. `int64`)."""
    if isinstance(scalar, LiteralScalar):
        return "Literal"
    if isinstance(scalar, AnyScalar):
        return "Any"
    mapping = get_type_mapping(scalar.base_type)
    if mapping is None and scalar.source_type is not None:
        mapping = get_type_mapping(scalar.source_type.__name__)
    if mapping is not None:
        return mapping.markdown
    return scalar.base_type


def _format_map(shape: MapOf, ctx: LinkContext | None) -> str:
    """Format a `MapOf` as a bare `map<K, V>` code span (no outer wrappers)."""
    key = _markdown_name_for_shape(shape.key)
    value = _markdown_name_for_shape(shape.value)
    return f"`map<{key}, {value}>`"


def _markdown_name_for_shape(shape: FieldShape) -> str:
    """Return a bare markdown name (no link, no backticks) for a shape.

    Used inside `map<K, V>` rendering. Picks the semantic NewType name
    when wrapping a registered primitive, otherwise the registry name
    of the terminal scalar.
    """
    if isinstance(shape, NewTypeShape):
        return shape.name
    if isinstance(shape, Scalar):
        return _registry_name(shape)
    if isinstance(shape, ModelRef):
        return shape.model.name
    if isinstance(shape, ArrayOf):
        inner = _markdown_name_for_shape(shape.element)
        return f"list<{inner}>"
    if isinstance(shape, MapOf):
        return (
            f"map<{_markdown_name_for_shape(shape.key)}, "
            f"{_markdown_name_for_shape(shape.value)}>"
        )
    return "?"


def format_type(field: FieldSpec, ctx: LinkContext | None = None) -> str:
    """Format a field's type for markdown display, with links and qualifiers."""
    qualifiers: list[str] = []
    display = _format_shape(field.shape, ctx, qualifiers)
    if not field.is_required:
        qualifiers.append("optional")
    if qualifiers:
        return f"{display} ({', '.join(qualifiers)})"
    return display


def _format_shape(
    shape: FieldShape, ctx: LinkContext | None, qualifiers: list[str]
) -> str:
    """Format a `FieldShape`, possibly appending qualifiers like `list`, `map`."""
    outer_depth, inner = _peel_arrays(shape)

    match inner:
        case LiteralScalar(values=values):
            if outer_depth > 0:
                inside = " | ".join(f'"{v}"' for v in values)
                return _plain_list_type(inside, outer_depth)
            return _format_literal(values)

        case UnionRef(union=u):
            if outer_depth > 0:
                qualifiers.append("list")
            return _format_union_members(u.members, ctx)

        case MapOf() as m:
            map_str = _format_map(m, ctx)
            if outer_depth > 0:
                return _wrap_list_n(map_str.strip("`"), outer_depth)
            return map_str

        case ModelRef() as m:
            link = _model_link(m, ctx)
            if outer_depth > 0:
                return _wrap_list_n(link, outer_depth)
            return link

        case NewTypeShape(name=name, ref=ref, inner=nt_inner):
            link = resolve_type_link(TypeIdentity(ref, name), ctx)
            if outer_depth > 0:
                return _wrap_list_n(link, outer_depth)
            if isinstance(nt_inner, ArrayOf):
                qualifiers.append("list")
            elif isinstance(nt_inner, MapOf):
                qualifiers.append("map")
            return link

        case Primitive() | AnyScalar() as s:
            text, linked = _scalar_display(s, ctx)
            if outer_depth > 0:
                if linked:
                    return _wrap_list_n(text, outer_depth)
                return _plain_list_type(text.strip("`"), outer_depth)
            return text

    raise TypeError(f"Unhandled FieldShape: {shape!r}")


# ---- Underlying-type rendering for NewType pages ----


def _peel_to_terminal(shape: FieldShape) -> FieldShape:
    """Strip `NewTypeShape` / `ArrayOf` layers to find the terminal shape."""
    while True:
        if isinstance(shape, NewTypeShape):
            shape = shape.inner
        elif isinstance(shape, ArrayOf):
            shape = shape.element
        else:
            return shape


def _linked_or_backticked(
    shape: FieldShape, ctx: LinkContext | None
) -> tuple[str, bool]:
    """Return (formatted_string, has_link) for a shape component.

    Used by NewType page rendering to format the underlying type with
    a link to its source page when one exists.
    """
    identity: TypeIdentity | None = None
    _, cur = _peel_arrays(shape)
    if isinstance(cur, NewTypeShape) and is_semantic_newtype(shape):
        identity = TypeIdentity(cur.ref, cur.name)
    elif isinstance(cur, Primitive) and cur.source_type is not None:
        src = cur.source_type
        if isinstance(src, type) and (
            issubclass(src, Enum) or issubclass(src, BaseModel)
        ):
            identity = TypeIdentity(src, cur.base_type)
    if identity and ctx:
        href = ctx.resolve_link(identity)
        if href:
            return _code_link(identity.name, href), True
    return _markdown_name_for_underlying(shape), False


def _markdown_name_for_underlying(shape: FieldShape) -> str:
    """Bare markdown display name for a NewType's underlying type."""
    if is_semantic_newtype(shape):
        _, cur = _peel_arrays(shape)
        if isinstance(cur, NewTypeShape):
            return cur.name
    return resolve_type_name(shape)


def format_underlying_type(shape: FieldShape, ctx: LinkContext | None = None) -> str:
    """Format a NewType's underlying type for the page header, with links."""
    terminal = _peel_to_terminal(shape)
    if isinstance(terminal, UnionRef):
        return _format_union_members(terminal.union.members, ctx, separator=" | ")

    if isinstance(terminal, MapOf):
        key_str, key_linked = _linked_or_backticked(terminal.key, ctx)
        val_str, val_linked = _linked_or_backticked(terminal.value, ctx)
        if key_linked or val_linked:
            if not key_linked:
                key_str = f"`{key_str}`"
            if not val_linked:
                val_str = f"`{val_str}`"
            return f"`map<`{key_str}`,`{val_str}`>`"
        return f"`map<{key_str}, {val_str}>`"

    # For underlying-type rendering on a NewType's own page, skip the
    # is_semantic_newtype path to avoid self-linking: this shape
    # belongs to the NewType being rendered.
    identity: TypeIdentity | None = None
    if isinstance(terminal, Primitive) and terminal.source_type is not None:
        src = terminal.source_type
        if isinstance(src, type) and (
            issubclass(src, Enum) or issubclass(src, BaseModel)
        ):
            identity = TypeIdentity.of(src)

    depth, _ = _peel_arrays(shape)

    if identity and ctx:
        href = ctx.resolve_link(identity)
        if href:
            linked = _code_link(identity.name, href)
            if depth > 0:
                return _wrap_list_n(linked, depth)
            return linked

    base = identity.name if identity else resolve_type_name(shape)
    if depth > 0:
        return _plain_list_type(base, depth)
    return f"`{base}`"
