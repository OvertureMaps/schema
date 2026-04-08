"""Typing utilities for the Overture schema system."""

import types
from typing import Annotated, Any, Literal, Union, get_args, get_origin


def collect_types(tp: Any) -> set[type]:  # noqa: ANN401
    """Collect all concrete types from a type annotation.

    Recursively unwraps ``Annotated``, ``NewType``, ``Union``/``X | Y``, and
    ``Literal`` to collect the concrete types they contain. Only actual `type`
    instances are returned.

    Parameters
    ----------
    tp : Any
        A type annotation to inspect.

    Returns
    -------
    set[type]
        All concrete types found within ``tp``.

    """
    result: set[type] = set()

    def _visit(t: Any) -> None:
        origin = get_origin(t)
        if origin is Annotated:
            _visit(get_args(t)[0])
        elif hasattr(t, "__supertype__"):
            _visit(t.__supertype__)
        elif origin is Union or origin is types.UnionType:
            for arg in get_args(t):
                _visit(arg)
        elif origin is Literal:
            for val in get_args(t):
                result.add(type(val))
        elif isinstance(t, type):
            result.add(t)

    _visit(tp)
    return result
