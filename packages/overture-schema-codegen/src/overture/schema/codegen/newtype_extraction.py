"""NewType extraction."""

from .docstring import clean_docstring, is_custom_docstring
from .specs import NewTypeSpec
from .type_analyzer import analyze_type

__all__ = ["extract_newtype"]


def extract_newtype(newtype_callable: object) -> NewTypeSpec:
    """Extract NewType specification from a NewType callable."""
    type_info = analyze_type(newtype_callable)
    doc = getattr(newtype_callable, "__doc__", None)
    name = type_info.newtype_name or getattr(newtype_callable, "__name__", None)
    if name is None:
        msg = f"Cannot determine name for NewType: {newtype_callable!r}"
        raise ValueError(msg)
    description = (
        clean_docstring(doc) if is_custom_docstring(doc) else type_info.description
    )
    return NewTypeSpec(
        name=name,
        description=description,
        type_info=type_info,
        source_type=newtype_callable,
    )
