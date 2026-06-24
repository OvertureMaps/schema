"""Low-level utilities for the conformance test harness.

Internal to the harness — not imported directly by generated test files.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from overture.schema.system.field_path import ArraySegment, FieldPath, coerce


def deep_merge(base: dict, scaffold: dict) -> dict:
    """Recursively merge scaffold onto a deep copy of base.

    Dict values merge recursively. All other values (including lists)
    in scaffold replace the corresponding base values; scaffold values
    are deep-copied so callers cannot accidentally share state with
    the merged result. Keys present in base but absent from scaffold
    are preserved.
    """
    result = copy.deepcopy(base)
    for key, value in scaffold.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class PathTraversalError(Exception):
    """Raised when path traversal cannot proceed."""


def _scaffold_struct(target: dict, name: str) -> dict:
    """Return `target[name]` as a dict, scaffolding `{}` when missing or None."""
    child = target.get(name) if isinstance(target, dict) else None
    if child is None:
        child = {}
        target[name] = child
    return child


def _scaffold_array(target: dict, name: str, path: FieldPath | str) -> list:
    """Return `target[name]` as a list, scaffolding `[{}]` when None.

    Empty arrays raise — there is no element to mutate.
    """
    child = target.get(name) if isinstance(target, dict) else None
    if child is None:
        child = [{}]
        target[name] = child
    if not isinstance(child, list):
        raise PathTraversalError(
            f"Expected list at '{name}' in path '{path}', got {type(child).__name__}"
        )
    if len(child) == 0:
        raise PathTraversalError(f"Empty array at '{name}' in path '{path}'")
    return child


def _descend_through_array(
    segment: ArraySegment, target: dict, path: FieldPath | str
) -> list:
    """Enter an array segment and walk through its `iter_count`.

    Scaffolds `[{}]` at the outer level when None; deeper levels
    (`iter_count > 1`) must already be lists — scaffolding into
    nested-list shapes isn't supported because no current schema
    needs it.

    Returns the innermost list. For terminal use, write to `[0]`;
    for intermediate use, the next segment lives in `[0]`.
    """
    container = _scaffold_array(target, segment.name, path)
    for _ in range(segment.iter_count - 1):
        if len(container) == 0 or not isinstance(container[0], list):
            raise PathTraversalError(
                f"Expected non-empty nested list at '{segment.name}' in path '{path}'"
            )
        container = container[0]
    return container


def set_at_path(path: FieldPath | str, value: object) -> Callable[[dict], dict]:
    """Return a mutator that sets *value* at *path* in a deep copy of the row.

    `[]` always indexes element 0 — one bad element suffices to trigger
    a violation since `validate()` checks are element-wise.

    None at an intermediate struct segment is scaffolded as `{}`; None at
    an intermediate array segment is scaffolded as `[{}]`. Empty arrays
    raise `PathTraversalError` when called — there is no element to mutate.

    Parameters
    ----------
    path
        A `FieldPath` or its canonical encoded form (`"rules[].tags[].v"`).
    value
        The value to set at the resolved path.

    Returns
    -------
    Callable[[dict], dict]
        A function that takes a row dict and returns a deep copy with the
        value at `path` replaced.

    Raises
    ------
    PathTraversalError
        When the path is empty, or when an intermediate or final array
        segment is empty (raised at call time, not at factory time).
    """
    segments = coerce(path).segments

    def mutator(row_dict: dict) -> dict:
        if not segments:
            raise PathTraversalError(f"Empty path: {path!r}")
        result = copy.deepcopy(row_dict)
        target: Any = result
        for segment in segments[:-1]:
            if isinstance(segment, ArraySegment):
                target = _descend_through_array(segment, target, path)[0]
            else:
                target = _scaffold_struct(target, segment.name)
        last = segments[-1]
        if isinstance(last, ArraySegment):
            _descend_through_array(last, target, path)[0] = value
        else:
            target[last.name] = value
        return result

    return mutator
