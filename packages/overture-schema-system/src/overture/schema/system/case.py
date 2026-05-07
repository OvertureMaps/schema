"""PascalCase to snake_case conversion."""

import re

__all__ = ["to_snake_case"]

_ACRONYM_BOUNDARY = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case.

    Handles acronym runs correctly: "HTMLParser" becomes "html_parser",
    not "h_t_m_l_parser".

    >>> to_snake_case("HTMLParser")
    'html_parser'
    >>> to_snake_case("BuildingPart")
    'building_part'
    >>> to_snake_case("simple")
    'simple'
    """
    name = _ACRONYM_BOUNDARY.sub(r"\1_\2", name)
    name = _CAMEL_BOUNDARY.sub(r"\1_\2", name)
    return name.lower()
