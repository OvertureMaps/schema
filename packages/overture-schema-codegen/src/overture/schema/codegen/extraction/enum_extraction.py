"""Enum extraction."""

from enum import Enum

from .docstring import clean_docstring, is_custom_docstring
from .specs import EnumMemberSpec, EnumSpec

__all__ = ["extract_enum"]


def extract_enum(enum_class: type[Enum]) -> EnumSpec:
    """Extract enum specification from an Enum class.

    Handles both simple str Enums and DocumentedEnums where members
    have per-value descriptions via the __doc__ attribute.
    """
    class_doc = enum_class.__doc__
    description = clean_docstring(class_doc) if is_custom_docstring(class_doc) else None

    members: list[EnumMemberSpec] = []
    for member in enum_class:
        member_doc = getattr(member, "__doc__", None)
        member_description = (
            member_doc if is_custom_docstring(member_doc, class_doc) else None
        )

        members.append(
            EnumMemberSpec(
                name=member.name,
                value=str(member.value),
                description=member_description,
            )
        )

    return EnumSpec(
        name=enum_class.__name__,
        description=description,
        members=members,
        source_type=enum_class,
    )
