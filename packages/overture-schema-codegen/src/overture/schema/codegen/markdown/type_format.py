"""Format TypeInfo as markdown type strings with cross-page links."""

from __future__ import annotations

from pydantic import BaseModel

from ..extraction.specs import FieldSpec, TypeIdentity
from ..extraction.type_analyzer import TypeInfo, TypeKind
from ..extraction.type_registry import is_semantic_newtype, resolve_type_name
from .link_computation import LinkContext

__all__ = [
    "format_dict_type",
    "format_type",
    "format_underlying_type",
    "resolve_type_link",
]


def _code_link(name: str, href: str) -> str:
    """Format a markdown link with inline-code text: [`name`](href)."""
    return f"[`{name}`]({href})"


def resolve_type_link(identity: TypeIdentity, ctx: LinkContext | None = None) -> str:
    """Resolve a TypeIdentity to a linked code span or plain code span.

    When *ctx* is provided, links only to types in the registry (types
    without pages render as inline code). Without context, renders as
    inline code -- producing a link requires a placement registry to
    compute correct relative paths.
    """
    if ctx:
        href = ctx.resolve_link(identity)
        if href:
            return _code_link(identity.name, href)
    return f"`{identity.name}`"


def _wrap_list_n(inner: str, depth: int) -> str:
    """Wrap an inner type string in `list<...>` markdown syntax *depth* times.

    Builds a single broken-backtick wrapper rather than nesting iteratively.
    Iterative nesting creates adjacent backticks that CommonMark
    interprets as multi-backtick code span delimiters.
    """
    return f"`{'list<' * depth}`{inner}`{'>' * depth}`"


def _plain_list_type(base: str, depth: int) -> str:
    """Format a plain (unlinked) list type string for *depth* nesting levels."""
    return f"`{'list<' * depth}{base}{'>' * depth}`"


def _linked_type_identity(ti: TypeInfo) -> TypeIdentity | None:
    """Return the TypeIdentity to use for a markdown link, or None for non-linked types."""
    if is_semantic_newtype(ti) and ti.newtype_ref is not None:
        assert ti.newtype_name is not None  # guaranteed by is_semantic_newtype
        return TypeIdentity(ti.newtype_ref, ti.newtype_name)
    if ti.kind in (TypeKind.ENUM, TypeKind.MODEL) and ti.source_type is not None:
        return TypeIdentity(ti.source_type, ti.base_type)
    return None


def _try_primitive_link(
    ti: TypeInfo, display_name: str, ctx: LinkContext | None
) -> str | None:
    """Try to link a PRIMITIVE type to its page via registry lookup.

    Registered primitives (int32, Geometry) and Pydantic types (HttpUrl)
    can have pages in the registry. Uses the type registry display name
    (e.g. `geometry` not `Geometry`) for the link text.
    """
    if ti.kind != TypeKind.PRIMITIVE or not ctx:
        return None
    candidate = ti.newtype_ref or ti.source_type
    if candidate is None:
        return None
    href = ctx.resolve_link(TypeIdentity(candidate, display_name))
    if href:
        return _code_link(display_name, href)
    return None


def _markdown_type_name(ti: TypeInfo) -> str:
    """Return the markdown display name for a type.

    Uses the semantic NewType name when present (e.g. `LanguageTag`),
    otherwise falls back to the resolved markdown type (e.g. `string`).
    """
    name = ti.newtype_name if is_semantic_newtype(ti) else None
    return name or resolve_type_name(ti, "markdown")


def format_dict_type(ti: TypeInfo) -> str:
    """Format a dict TypeInfo as bare `map<K, V>` using resolved markdown names."""
    if ti.dict_key_type is None or ti.dict_value_type is None:
        msg = f"format_dict_type requires dict key/value types, got {ti}"
        raise ValueError(msg)
    key = _markdown_type_name(ti.dict_key_type)
    value = _markdown_type_name(ti.dict_value_type)
    return f"map<{key}, {value}>"


def _format_union_members(
    members: tuple[type[BaseModel], ...],
    ctx: LinkContext | None,
    separator: str = r" \| ",
) -> str:
    r"""Format union members as individually linked/backticked names.

    Each member is resolved independently so members with pages get linked
    while others render as plain code spans. *separator* is inserted between
    members (default is `\|` for table-cell safety).
    """
    return separator.join(resolve_type_link(TypeIdentity.of(m), ctx) for m in members)


def format_type(
    field: FieldSpec,
    ctx: LinkContext | None = None,
) -> str:
    """Format a field's type for markdown display, with links and qualifiers."""
    ti = field.type_info
    qualifiers: list[str] = []

    if ti.kind == TypeKind.LITERAL and ti.literal_values:
        if len(ti.literal_values) == 1:
            return f'`"{ti.literal_values[0]}"`'
        return r" \| ".join(f'`"{v}"`' for v in ti.literal_values)

    identity = _linked_type_identity(ti)

    if ti.kind == TypeKind.UNION and ti.union_members:
        display = _format_union_members(ti.union_members, ctx)
        if ti.is_list:
            qualifiers.append("list")
    elif ti.is_dict:
        if identity:
            display = resolve_type_link(identity, ctx)
            qualifiers.append("map")
        else:
            display = f"`{format_dict_type(ti)}`"
    elif identity:
        display = resolve_type_link(identity, ctx)
        # List layers outside a NewType wrap with list<> syntax (e.g., list[PhoneNumber]
        # renders as list<PhoneNumber>). List layers inside a NewType use a (list)
        # qualifier instead (e.g., Sources wrapping list[SourceItem] renders as
        # Sources (list)), since the list-ness is an implementation detail of the type.
        if ti.newtype_outer_list_depth > 0:
            assert ti.is_list  # outer list layers are a subset of total list layers
            display = _wrap_list_n(display, ti.newtype_outer_list_depth)
        elif ti.is_list and ti.newtype_name is not None:  # list is inside the NewType
            qualifiers.append("list")
        elif ti.is_list:
            display = _wrap_list_n(display, ti.list_depth)
    else:
        # Fallback: types without a linked identity. Registered primitives (int32,
        # Geometry) and Pydantic types (HttpUrl) may still link to aggregate pages
        # via the placement registry. Unregistered primitives render as plain code.
        base = resolve_type_name(ti, "markdown")
        link = _try_primitive_link(ti, base, ctx)
        if link and ti.is_list:
            display = _wrap_list_n(link, ti.list_depth)
        elif link:
            display = link
        elif ti.is_list:
            display = _plain_list_type(base, ti.list_depth)
        else:
            display = f"`{base}`"

    if not field.is_required:
        qualifiers.append("optional")

    if qualifiers:
        return f"{display} ({', '.join(qualifiers)})"
    return display


def _linked_or_backticked(ti: TypeInfo, ctx: LinkContext | None) -> tuple[str, bool]:
    """Return (formatted_string, has_link) for a TypeInfo component.

    Used by format_underlying_type to decide whether container types
    need broken-backtick formatting (interleaving backtick runs with
    linked text).

    When `has_link` is True, `formatted_string` is a markdown link
    ready for broken-backtick container syntax. When False, it is a raw
    name that the caller embeds inside backticks.
    """
    identity = _linked_type_identity(ti)
    if identity and ctx:
        href = ctx.resolve_link(identity)
        if href:
            return _code_link(identity.name, href), True
    return _markdown_type_name(ti), False


def format_underlying_type(ti: TypeInfo, ctx: LinkContext | None = None) -> str:
    """Format a NewType's underlying type for the page header, with links.

    Links enums and models that have their own pages. Does not link the
    outermost NewType (which would self-reference). Dict key/value types
    use full link resolution since they reference other types.
    """
    if ti.kind == TypeKind.UNION and ti.union_members:
        return _format_union_members(ti.union_members, ctx, separator=" | ")

    if ti.is_dict and ti.dict_key_type and ti.dict_value_type:
        key_str, key_linked = _linked_or_backticked(ti.dict_key_type, ctx)
        val_str, val_linked = _linked_or_backticked(ti.dict_value_type, ctx)
        if key_linked or val_linked:
            if not key_linked:
                key_str = f"`{key_str}`"
            if not val_linked:
                val_str = f"`{val_str}`"
            return f"`map<`{key_str}`,`{val_str}`>`"
        return f"`map<{key_str}, {val_str}>`"

    # Only link enums and models -- skip is_semantic_newtype to avoid
    # self-linking (this TypeInfo belongs to the NewType being rendered).
    identity = (
        TypeIdentity.of(ti.source_type)
        if ti.kind in (TypeKind.ENUM, TypeKind.MODEL) and ti.source_type
        else None
    )
    if identity and ctx:
        href = ctx.resolve_link(identity)
        if href:
            linked = _code_link(identity.name, href)
            if ti.is_list:
                return _wrap_list_n(linked, ti.list_depth)
            return linked

    base = identity.name if identity else resolve_type_name(ti, "markdown")
    if ti.is_list:
        return _plain_list_type(base, ti.list_depth)
    return f"`{base}`"
