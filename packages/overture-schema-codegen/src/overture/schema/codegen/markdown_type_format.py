"""Format TypeInfo as markdown type strings with cross-page links."""

from __future__ import annotations

from pydantic import BaseModel

from .link_computation import LinkContext
from .specs import FieldSpec
from .type_analyzer import TypeInfo, TypeKind
from .type_registry import is_semantic_newtype, resolve_type_name

__all__ = ["format_dict_type", "format_type", "format_underlying_type"]


def _code_link(name: str, href: str) -> str:
    """Format a markdown link with inline-code text: [``name``](href)."""
    return f"[`{name}`]({href})"


def _resolve_type_link(type_name: str, ctx: LinkContext | None = None) -> str:
    """Resolve a type name to a linked code span or plain code span.

    When *ctx* is provided, links only to types in the registry (types
    without pages render as inline code). Without context, renders as
    inline code -- producing a link requires a placement registry to
    compute correct relative paths.
    """
    if ctx:
        href = ctx.resolve_link(type_name)
        if href:
            return _code_link(type_name, href)
    return f"`{type_name}`"


def _wrap_list(inner: str) -> str:
    """Wrap an inner type string in list<...> markdown syntax."""
    return f"`list<`{inner}`>`"


def _linked_type_name(ti: TypeInfo) -> str | None:
    """Return the name to use for a markdown link, or None for non-linked types."""
    if is_semantic_newtype(ti):
        return ti.newtype_name
    if ti.kind in (TypeKind.ENUM, TypeKind.MODEL):
        return ti.base_type
    return None


def _markdown_type_name(ti: TypeInfo) -> str:
    """Return the markdown display name for a type.

    Uses the semantic NewType name when present (e.g. ``LanguageTag``),
    otherwise falls back to the resolved markdown type (e.g. ``string``).
    """
    name = ti.newtype_name if is_semantic_newtype(ti) else None
    return name or resolve_type_name(ti, "markdown")


def format_dict_type(ti: TypeInfo) -> str:
    """Format a dict TypeInfo as bare ``map<K, V>`` using resolved markdown names."""
    assert ti.dict_key_type is not None
    assert ti.dict_value_type is not None
    key = _markdown_type_name(ti.dict_key_type)
    value = _markdown_type_name(ti.dict_value_type)
    return f"map<{key}, {value}>"


def _format_union_members(
    members: tuple[type[BaseModel], ...],
    ctx: LinkContext | None,
    separator: str = r" \| ",
) -> str:
    """Format union members as individually linked/backticked names.

    Each member is resolved independently so members with pages get linked
    while others render as plain code spans. *separator* is inserted between
    members (default is ``\\|`` for table-cell safety).
    """
    return separator.join(
        _resolve_type_link(member.__name__, ctx) for member in members
    )


def format_type(
    field: FieldSpec,
    ctx: LinkContext | None = None,
) -> str:
    """Format a field's type for markdown display, with links and qualifiers."""
    ti = field.type_info
    qualifiers: list[str] = []

    if ti.kind == TypeKind.LITERAL and ti.literal_value is not None:
        return f'`"{ti.literal_value}"`'

    link_name = _linked_type_name(ti)

    if ti.kind == TypeKind.UNION and ti.union_members:
        display = _format_union_members(ti.union_members, ctx)
        if ti.is_list:
            qualifiers.append("list")
    elif ti.is_dict:
        if link_name:
            display = _resolve_type_link(link_name, ctx)
            qualifiers.append("map")
        else:
            display = f"`{format_dict_type(ti)}`"
    elif link_name:
        display = _resolve_type_link(link_name, ctx)
        if ti.is_list and link_name == ti.newtype_name:
            qualifiers.append("list")
        elif ti.is_list:
            display = _wrap_list(display)
    else:
        base = resolve_type_name(ti, "markdown")
        if ti.is_list:
            display = f"`list<{base}>`"
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

    When ``has_link`` is True, ``formatted_string`` is a markdown link
    ready for broken-backtick container syntax. When False, it is a raw
    name that the caller embeds inside backticks.
    """
    link_name = _linked_type_name(ti)
    if link_name and ctx:
        href = ctx.resolve_link(link_name)
        if href:
            return _code_link(link_name, href), True
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

    # Only link enums and models — skip is_semantic_newtype to avoid
    # self-linking (this TypeInfo belongs to the NewType being rendered).
    # Use source_type.__name__ rather than base_type: base_type may be
    # the outermost NewType name when only one NewType wraps a class.
    link_name = (
        ti.source_type.__name__
        if ti.kind in (TypeKind.ENUM, TypeKind.MODEL) and ti.source_type
        else None
    )
    if link_name and ctx:
        href = ctx.resolve_link(link_name)
        if href:
            linked = _code_link(link_name, href)
            if ti.is_list:
                return _wrap_list(linked)
            return linked

    base = link_name or resolve_type_name(ti, "markdown")
    if ti.is_list:
        return f"`list<{base}>`"
    return f"`{base}`"
