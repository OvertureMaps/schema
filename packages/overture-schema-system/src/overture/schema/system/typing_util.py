"""Typing utilities for the Overture schema system."""

import types
from typing import Annotated, Any, Union, cast, get_args, get_origin

from pydantic import RootModel
from typing_extensions import TypeForm


def denoted_type(tp: TypeForm[object]) -> TypeForm[object]:
    """Return the type a `RootModel` denotes: its root, as written.

    Pydantic lifts a root's `Field(...)` -- notably `discriminator` -- off
    the annotation onto the root `FieldInfo`, leaving
    `model_fields["root"].annotation` a bare type. Reattaching that
    `FieldInfo` reconstructs the annotation the RootModel was declared
    over, so a caller sees the same type expression it would for the
    equivalent bare alias. A RootModel over another RootModel denotes what
    its innermost root denotes.

    Parameters
    ----------
    tp : TypeForm[object]
        A type annotation. Anything other than a `RootModel` subclass is
        returned unchanged.

    Returns
    -------
    TypeForm[object]
        `Annotated[root, root_field_info, ...]` for a RootModel, with one
        `FieldInfo` per peeled layer; otherwise `tp`.

    Raises
    ------
    TypeError
        If a RootModel's root leads back to itself, which denotes nothing,
        or has no annotation.
    """
    peeled: list[type[RootModel]] = []
    while isinstance(tp, type) and issubclass(tp, RootModel):
        if tp in peeled:
            raise TypeError(
                f"Self-referential RootModel {tp.__name__} is not supported"
            )
        peeled.append(tp)
        root = tp.model_fields["root"].annotation
        if root is None:
            raise TypeError(f"RootModel {tp.__name__} has no root annotation")
        tp = root
    # Wrap innermost layer first; nested `Annotated` flattens, so the result
    # lists each root `FieldInfo` from the innermost out. `Annotated` over a
    # variable is built at runtime, which mypy cannot check as a `TypeForm`.
    for layer in reversed(peeled):
        tp = cast(TypeForm[object], Annotated[tp, layer.model_fields["root"]])
    return tp


def collect_types(tp: TypeForm[object]) -> set[type]:
    """Collect concrete classes referenced by a type annotation.

    Unwraps `Annotated[X, ...]` and `Union[X, Y]` (including `X | Y`) to
    find concrete `type` objects. Used by tag providers to walk
    discriminated-union features (e.g. `Segment`) into their member
    classes.

    Only handles the cases the discovery system encounters today.
    `overture-schema-codegen` has a more capable
    `analyze_type` (`extraction/type_analyzer.py`) that also unwraps
    `NewType`, `Literal`, `list[...]`, `dict[K, V]`, and accumulates
    constraints. A future work item is to consolidate this and the
    similar logic in `overture-schema-cli` against that implementation.

    Parameters
    ----------
    tp : TypeForm[object]
        A type annotation. Typically a class, an `Annotated[...]`
        wrapper, or a discriminated union of classes.

    Returns
    -------
    set[type]
        Concrete classes reachable through `Annotated` and `Union`
        unwrapping. Other type expressions yield an empty set.

    """
    result: set[type] = set()

    def _visit(t: Any) -> None:
        origin = get_origin(t)
        if origin is Annotated:
            _visit(get_args(t)[0])
        elif origin is Union or origin is types.UnionType:
            for arg in get_args(t):
                _visit(arg)
        elif isinstance(t, type):
            result.add(t)

    _visit(tp)
    return result
