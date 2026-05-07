"""NewType extraction."""

from .docstring import clean_docstring, is_custom_docstring
from .field import NewTypeShape
from .specs import NewTypeSpec
from .type_analyzer import analyze_type

__all__ = ["extract_newtype"]


def extract_newtype(newtype_callable: object) -> NewTypeSpec:
    """Extract a `NewTypeSpec` from a NewType callable.

    `analyze_type(newtype_callable)` returns a shape whose outermost
    layer is the NewType's own `NewTypeShape`. We strip that wrapper so
    `NewTypeSpec.shape` describes the *underlying* type -- the NewType
    isn't a self-reference on its own page.
    """
    shape, _, ti_description = analyze_type(newtype_callable)

    name = getattr(newtype_callable, "__name__", None)
    if isinstance(shape, NewTypeShape) and shape.name == name:
        underlying = shape.inner
    else:
        underlying = shape

    if name is None:
        msg = f"Cannot determine name for NewType: {newtype_callable!r}"
        raise ValueError(msg)

    doc = getattr(newtype_callable, "__doc__", None)
    description = clean_docstring(doc) if is_custom_docstring(doc) else ti_description

    return NewTypeSpec(
        name=name,
        description=description,
        shape=underlying,
        source_type=newtype_callable,
    )
