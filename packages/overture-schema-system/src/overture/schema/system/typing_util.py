"""Typing utilities for the Overture schema system."""

import types
from typing import Annotated, Any, Union, get_args, get_origin


def collect_types(tp: Any) -> set[type]:  # noqa: ANN401
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
    tp
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
