"""Docstring extraction and cleaning utilities."""

import inspect
from enum import Enum
from typing import NewType

__all__ = ["clean_docstring", "first_docstring_line", "is_custom_docstring"]


# Probe auto-generated docstrings so we can distinguish them from explicit ones.
# Both Enum and NewType generate default docstrings that vary by Python version;
# capturing at import time adapts automatically if the format changes.
class _DocstringProbeEnum(Enum):
    pass


_ENUM_DEFAULT_DOCSTRING = _DocstringProbeEnum.__doc__
del _DocstringProbeEnum
_NewtypeProbe = NewType("_NewtypeProbe", int)
_NEWTYPE_DEFAULT_DOCSTRING = _NewtypeProbe.__doc__
del _NewtypeProbe


def clean_docstring(doc: str | None) -> str | None:
    """Return cleaned docstring, or None if absent or whitespace-only."""
    if not doc:
        return None
    cleaned = inspect.cleandoc(doc)
    return cleaned or None


def first_docstring_line(doc: str | None) -> str:
    """Return the first line of a docstring, or empty string."""
    cleaned = clean_docstring(doc)
    if not cleaned:
        return ""
    return cleaned.split("\n")[0]


def is_custom_docstring(doc: str | None, inherited_doc: str | None = None) -> bool:
    """Check if a docstring was explicitly written, not auto-generated or inherited."""
    return bool(doc) and doc not in (
        _ENUM_DEFAULT_DOCSTRING,
        _NEWTYPE_DEFAULT_DOCSTRING,
        inherited_doc,
    )
