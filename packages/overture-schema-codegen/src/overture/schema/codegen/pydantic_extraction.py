"""Pydantic built-in type extraction."""

import re

from .docstring import first_docstring_line
from .specs import PydanticTypeSpec

__all__ = ["extract_pydantic_type"]

# Matches bare admonition labels like "Info:" or "Note:" with no following text.
_ADMONITION_LABEL = re.compile(r"^\w+:\s*$")


def _usable_description(doc: str | None) -> str | None:
    """Return the first docstring line, or None if it's an admonition label."""
    line = first_docstring_line(doc)
    if line is None or _ADMONITION_LABEL.match(line):
        return None
    return line


def extract_pydantic_type(cls: type) -> PydanticTypeSpec:
    """Extract a PydanticTypeSpec from a Pydantic built-in type class."""
    module = getattr(cls, "__module__", "")
    if not module.startswith("pydantic"):
        msg = f"Expected a pydantic type, got {cls!r} from {module!r}"
        raise ValueError(msg)
    return PydanticTypeSpec(
        name=cls.__name__,
        description=_usable_description(cls.__doc__),
        source_type=cls,
        source_module=cls.__module__.removeprefix("pydantic."),
    )
