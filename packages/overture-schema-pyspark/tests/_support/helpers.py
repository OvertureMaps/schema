"""Low-level utilities for the conformance test harness.

Internal to the harness — not imported directly by generated test files.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from overture.schema.system.field_path import (
    ArraySegment,
    FieldPath,
    MapProjection,
    MapSegment,
    coerce,
)


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


def _require_non_empty_list(target: object, path: FieldPath | str) -> list:
    """Assert *target* is already a non-empty list, returning it.

    An anonymous `ArraySegment` descends one more list level via element 0
    with no field name to scaffold against, so its parent element must
    already be a list — deeper levels must already be lists, since
    scaffolding into nested-list shapes isn't supported (no current schema
    needs it).
    """
    if not isinstance(target, list):
        raise PathTraversalError(
            f"Expected nested list in path '{path}', got {type(target).__name__}"
        )
    if len(target) == 0:
        raise PathTraversalError(f"Empty nested list in path '{path}'")
    return target


def _array_slot(segment: ArraySegment, target: dict, path: FieldPath | str) -> list:
    """Return the list *segment* indexes into, scaffolding when named.

    A named segment enters an array field, scaffolding `[{}]` when it's
    None. An anonymous segment descends one more list level of the same
    field (`list[list[...]]`), which has no field name to scaffold
    against, so its parent element must already be a non-empty list.
    """
    if segment.is_anonymous:
        return _require_non_empty_list(target, path)
    return _scaffold_array(target, segment.name, path)


def set_at_path(path: FieldPath | str, value: object) -> Callable[[dict], dict]:
    """Return a mutator that sets *value* at *path* in a deep copy of the row.

    `[]` always indexes element 0 — one bad element suffices to trigger
    a violation since `validate()` checks are element-wise.

    None at an intermediate struct segment is scaffolded as `{}`; None at
    an intermediate array segment is scaffolded as `[{}]`. Empty arrays
    raise `PathTraversalError` when called — there is no element to mutate.

    A trailing map marker (`"items[].tags{value}"`, `"tags{key}"`) corrupts
    the single entry of the map it reaches: `{value}` replaces the entry's
    value, `{key}` replaces its key, each preserving the other side. A
    non-terminal `{value}` (`"subs{value}[]"`, `"subs{value}{value}"`)
    descends the sole entry's value and keeps navigating, so a map value that
    is itself a container is reachable. A non-terminal `{key}` raises — a map
    key is an immutable scalar with nothing to descend into.

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
        When the path is empty, when an intermediate or final array segment
        is empty, when a terminal map is missing or empty, or when a
        non-terminal `{key}` projection appears (raised at call time, not at
        factory time).
    """
    segments = coerce(path).segments

    def mutator(row_dict: dict) -> dict:
        if not segments:
            raise PathTraversalError(f"Empty path: {path!r}")
        result = copy.deepcopy(row_dict)
        target: Any = result
        for segment in segments[:-1]:
            if isinstance(segment, MapSegment):
                target = _descend_map_projection(segment, target, path)
            elif isinstance(segment, ArraySegment):
                target = _array_slot(segment, target, path)[0]
            else:
                target = _scaffold_struct(target, segment.name)
        last = segments[-1]
        if isinstance(last, MapSegment):
            _set_map_projection(last, target, path, value)
        elif isinstance(last, ArraySegment):
            _array_slot(last, target, path)[0] = value
        else:
            target[last.name] = value
        return result

    return mutator


def _map_at(segment: MapSegment, parent: object, path: FieldPath | str) -> dict:
    """Return the map *segment* projects, resolved from *parent*.

    A named segment reads the map at `parent[segment.name]`; an anonymous
    segment (the parent element is itself a map, e.g. `subs{value}{value}`)
    projects *parent* directly. Raises `PathTraversalError` when the map is
    missing or empty — there is no entry to descend or corrupt.
    """
    if segment.is_anonymous:
        m = parent
    else:
        m = parent.get(segment.name) if isinstance(parent, dict) else None
    if not isinstance(m, dict) or not m:
        where = "" if segment.is_anonymous else f" at '{segment.name}'"
        raise PathTraversalError(f"Missing or empty map{where} in path '{path}'")
    return m


def _descend_map_projection(
    segment: MapSegment, parent: object, path: FieldPath | str
) -> object:
    """Descend a non-terminal `{value}` projection into the sole entry's value.

    Returns the first entry's value so navigation continues into a container
    the map holds (`subs{value}[]`, `subs{value}{value}`). A `{key}` projection
    raises: a map key is an immutable scalar with nothing to descend into.
    """
    m = _map_at(segment, parent, path)
    if segment.projection is not MapProjection.VALUE:
        raise PathTraversalError(
            f"Non-terminal map key projection {segment.name!r} in path '{path}'; "
            f"a map key is a scalar and cannot be descended"
        )
    return m[next(iter(m))]


def _set_map_projection(
    segment: MapSegment, parent: object, path: FieldPath | str, value: object
) -> None:
    """Corrupt the single entry of the map *segment* names inside *parent*.

    A VALUE projection replaces the first entry's value with *value* (keeping
    its key); a KEY projection replaces the first entry's key with *value*
    (keeping its value). One bad entry suffices — map checks are element-wise,
    mirroring how `[]` mutates only element 0. Raises `PathTraversalError`
    when the map is missing or empty, since there is no entry to corrupt.
    """
    m = _map_at(segment, parent, path)
    first_key = next(iter(m))
    if segment.projection is MapProjection.VALUE:
        m[first_key] = value
    else:
        m[value] = m.pop(first_key)
