"""Type-alias extraction: NewType and RootModel into `NewTypeSpec`.

Both a NewType and a `RootModel` are named aliases over an underlying
type -- a RootModel serializes as its bare root value -- so both document
as the same `NewTypeSpec` (a name plus the underlying shape).
"""

from pydantic import RootModel

from .docstring import clean_docstring, is_custom_docstring
from .field import NewTypeShape
from .specs import NewTypeSpec
from .type_analyzer import analyze_type

__all__ = ["extract_newtype", "extract_rootmodel_alias"]


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


def extract_rootmodel_alias(root_model: type[RootModel]) -> NewTypeSpec:
    """Extract a `NewTypeSpec` documenting a `RootModel` as a named alias.

    `analyze_type` already unwraps a RootModel to its bare root shape, so
    there is no wrapper to strip -- unlike `extract_newtype`. A custom
    class docstring names the alias; otherwise the root field's own
    description stands in. Pydantic moves that description onto the root
    `FieldInfo` (as it does for model fields), so read it there rather than
    from `analyze_type`, which recurses past it.

    No `is_custom_docstring` guard is needed (again unlike `extract_newtype`):
    a RootModel subclass with no docstring has `__doc__ = None` -- classes do
    not inherit `RootModel`'s base docstring -- so there is no auto-generated
    text to filter out, and `clean_docstring(None)` falls through to the root
    description.
    """
    shape, _, _ = analyze_type(root_model)
    root = root_model.model_fields["root"]
    description = clean_docstring(root_model.__doc__) or root.description
    return NewTypeSpec(
        name=root_model.__name__,
        description=description,
        shape=shape,
        source_type=root_model,
    )
