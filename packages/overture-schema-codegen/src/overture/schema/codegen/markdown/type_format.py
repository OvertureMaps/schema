"""Format `FieldShape` trees as markdown type strings with cross-page links."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from pydantic import BaseModel
from typing_extensions import assert_never

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


def _model_ref_identity(model_ref: ModelRef) -> TypeIdentity | None:
    """Return a linkable identity for a `ModelRef`, or None when unsourced.

    A `ModelRef` links by its `source_type` (the original Python class)
    paired with the model name. Returns None when `source_type` is absent
    -- a synthesized spec with no backing class has no page to link to.
    """
    src = model_ref.model.source_type
    if src is None:
        return None
    return TypeIdentity(src, model_ref.model.name)


def _model_link(model_ref: ModelRef, ctx: LinkContext | None) -> str:
    """Resolve a `ModelRef` to a markdown link or fallback code span."""
    identity = _model_ref_identity(model_ref)
    if identity is not None:
        return resolve_type_link(identity, ctx)
    return f"`{model_ref.model.name}`"


def _scalar_identity(scalar: Primitive) -> TypeIdentity | None:
    """Return a linkable identity for a `Primitive`'s `source_type`, if any.

    Enum / BaseModel / Pydantic-sourced types link by their own
    identity and class name. Class-based registered primitives
    (`Geometry`, `BBox`) are plain classes -- not BaseModel, not
    Pydantic-sourced -- so they link by object identity to their
    aggregate page under the markdown registry name (`geometry`, `bbox`).
    """
    src = scalar.source_type
    if not isinstance(src, type):
        return None
    if issubclass(src, Enum) or issubclass(src, BaseModel) or is_pydantic_sourced(src):
        return TypeIdentity.of(src)
    if get_type_mapping(src.__name__) is not None:
        return TypeIdentity(src, _registry_name(scalar))
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
    """Format a `MapOf` as a `map<K, V>` code span, linking key/value types.

    Semantic NewTypes and Enum / BaseModel-sourced key/value types link
    to their pages; primitives stay bare. Output is identical whether the
    map is rendered in a field cell or as a NewType's underlying type --
    both paths route through here.

    A link has to break out of the surrounding code span, so any bare side
    is folded into the adjacent `map<...>` span rather than wrapped in its
    own backticks. Two backtick spans must never abut: CommonMark reads the
    resulting `` as a two-backtick delimiter and swallows the link.
    """
    key_str, key_linked = _map_side(shape.key, ctx)
    val_str, val_linked = _map_side(shape.value, ctx)
    if not key_linked and not val_linked:
        return f"`map<{key_str}, {val_str}>`"
    if key_linked and val_linked:
        return f"`map<`{key_str}`,`{val_str}`>`"
    if key_linked:
        return f"`map<`{key_str}`,{val_str}>`"
    return f"`map<{key_str},`{val_str}`>`"


def _map_side(shape: FieldShape, ctx: LinkContext | None) -> tuple[str, bool]:
    """Render one map key/value as (text, is_link).

    Returns a page link when the side resolves to one, else its
    container-aware bare name (so a `list<...>` / `map<...>` wrapper
    survives instead of collapsing to its element). The flag tells
    `_format_map` whether the side breaks out of the surrounding code span.
    """
    link = _map_side_link(shape, ctx)
    if link is not None:
        return link, True
    return _bare_map_side_name(shape), False


def _map_side_link(shape: FieldShape, ctx: LinkContext | None) -> str | None:
    """Return a markdown link for a map key/value that has its own page.

    Links a semantic NewType, a model (`ModelRef`), or an Enum /
    BaseModel-sourced primitive when `ctx` resolves a page for it.
    NewType and primitive sides link through `list<...>` layers; a model
    side links only when it is the direct map side (`depth == 0`), so a
    `list<Model>`-valued map keeps its `list<...>` wrapper from
    `_bare_map_side_name` rather than collapsing to a bare model link.
    Returns None when the side has no page; the caller renders a bare
    name instead.
    """
    identity: TypeIdentity | None = None
    depth, cur = _peel_arrays(shape)
    if isinstance(cur, NewTypeShape) and is_semantic_newtype(shape):
        identity = TypeIdentity(cur.ref, cur.name)
    elif depth == 0 and isinstance(cur, ModelRef):
        identity = _model_ref_identity(cur)
    elif isinstance(cur, Primitive) and cur.source_type is not None:
        src = cur.source_type
        if isinstance(src, type) and (
            issubclass(src, Enum) or issubclass(src, BaseModel)
        ):
            identity = TypeIdentity(src, cur.base_type)
    if identity and ctx:
        href = ctx.resolve_link(identity)
        if href:
            return _code_link(identity.name, href)
    return None


def _bare_map_side_name(shape: FieldShape) -> str:
    """Bare markdown name for a map key/value, recursing through containers.

    Every variant resolves to a real name: `list<...>` / `map<...>`
    wrappers recurse, scalars use their registry name (so `Any` is `Any`,
    not `?`), semantic NewTypes and models use their type name, and a
    pass-through NewType resolves through the registry like the scalar it
    aliases. There is no `?` fallback -- a side that can't be named is a
    bug, not a placeholder.

    A union-valued map is the one shape left unrendered: no schema field
    uses one, and its `\\|`-separated members do not compose cleanly into
    a bare `map<...>` span. It raises so the gap surfaces loudly when a
    field first needs it, rather than shipping a half-rendered value.
    """
    match shape:
        case ArrayOf(element=element):
            return f"list<{_bare_map_side_name(element)}>"
        case MapOf(key=key, value=value):
            return f"map<{_bare_map_side_name(key)}, {_bare_map_side_name(value)}>"
        case NewTypeShape(name=name) if is_semantic_newtype(shape):
            return name
        case NewTypeShape():
            return resolve_type_name(shape)
        case ModelRef(model=model):
            return model.name
        case Primitive() | LiteralScalar() | AnyScalar():
            return _registry_name(shape)
        case UnionRef():
            raise NotImplementedError(
                "union-typed map key/value is not rendered in markdown; "
                "add handling here when a schema field first needs one"
            )
        case _:
            assert_never(shape)


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


def format_underlying_type(shape: FieldShape, ctx: LinkContext | None = None) -> str:
    """Format a NewType's underlying type for the page header, with links."""
    terminal = _peel_to_terminal(shape)
    if isinstance(terminal, UnionRef):
        return _format_union_members(terminal.union.members, ctx, separator=" | ")

    if isinstance(terminal, MapOf):
        return _format_map(terminal, ctx)

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
