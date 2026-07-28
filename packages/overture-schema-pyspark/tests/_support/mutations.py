"""Model-level mutation functions for generated conformance tests.

Each function takes a row dict and returns a modified copy that should
trigger a specific model-level constraint violation. Generated test
files import these by name.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from overture.schema.system.field_path import (
    ArraySegment,
    Direct,
    FieldPath,
    FieldSegment,
    MapProjection,
    MapSegment,
    StructSegment,
    coerce,
    terminal_run_start,
)

from .helpers import PathTraversalError

_SENTINEL = "__FORBIDDEN_PRESENT__"
_NOT_EQUAL_PREFIX = "__NOT_"
_STUB_MAP_KEY = "_stub"


def mutate_require_any_of(
    row_dict: dict,
    field_names: list[FieldPath | str],
    *,
    array_path: FieldPath | str | None = None,
    struct_path: str | None = None,
    map_path: FieldPath | str | None = None,
    element_path: FieldPath | str | None = None,
) -> dict:
    """Null every named field so `require_any_of` fires.

    Parameters
    ----------
    array_path
        Array column the constrained model lives inside. When None, the
        fields live at the row root.
    struct_path
        Optional single intermediate struct field between the array
        element (or map value) and the target fields.
    map_path
        Map column whose `dict[K, Model]` value carries the constraint.
        Mutually exclusive with `array_path`.
    element_path
        Full element-relative descent to the constrained model, walked
        generically when the nesting mixes map and array boundaries
        (`subs{value}[]`, `items[].configs{value}`) that no scalar path
        expresses. Mutually exclusive with the scalar paths above.

    See `_null_all_named_fields` for the full nesting semantics.
    """
    return _null_all_named_fields(
        row_dict,
        field_names,
        array_path=array_path,
        struct_path=struct_path,
        map_path=map_path,
        element_path=element_path,
    )


def mutate_radio_group(row_dict: dict, field_names: list[FieldPath | str]) -> dict:
    """Set first two fields to True so radio_group fires."""
    result = copy.deepcopy(row_dict)
    for name in field_names[:2]:
        _set_nested(result, name, True)
    return result


def mutate_require_any_true(row_dict: dict, disabling_values: dict[str, Any]) -> dict:
    """Set each condition field to a value that makes its condition false.

    `require_any_true` fires only when no condition is true, so writing a
    value each condition rejects (e.g. `is_land=False` for
    `FieldEqCondition("is_land", True)`) makes them all false. The renderer
    computes the per-field disabling value from the constraint's conditions.
    """
    result = copy.deepcopy(row_dict)
    for name, value in disabling_values.items():
        _set_nested(result, name, value)
    return result


def mutate_min_fields_set(
    row_dict: dict,
    field_names: list[FieldPath | str],
    *,
    array_path: FieldPath | str | None = None,
    struct_path: str | None = None,
    map_path: FieldPath | str | None = None,
    element_path: FieldPath | str | None = None,
) -> dict:
    """Null every named field so `min_fields_set(N)` fires (0 < N).

    The descriptor enumerates every field of the constrained model, so
    nulling all of them drops the non-null count to zero -- below any
    positive `count`. Nulling required fields incidentally trips their
    `check_required` checks; the conformance test only asserts the
    expected violation is present, so the extra failures don't matter.

    `array_path` / `struct_path` / `map_path` / `element_path` mirror
    `mutate_require_any_of` for the case where the constrained model is
    reached through array or map iteration (and optionally one intermediate
    struct field, or a mixed map/array descent).
    """
    return _null_all_named_fields(
        row_dict,
        field_names,
        array_path=array_path,
        struct_path=struct_path,
        map_path=map_path,
        element_path=element_path,
    )


def _null_all_named_fields(
    row_dict: dict,
    field_names: list[FieldPath | str],
    *,
    array_path: FieldPath | str | None,
    struct_path: str | None,
    map_path: FieldPath | str | None = None,
    element_path: FieldPath | str | None = None,
) -> dict:
    """Return a deep copy of *row_dict* with every named field set to None.

    Without *array_path*, *map_path*, or *element_path*, the fields live at the
    row root. With *array_path*, the fields live inside elements of that array
    column; with *map_path*, inside the value model of that map column.
    *struct_path* names an optional single intermediate struct field between
    the array element / map value and the target fields. *element_path* carries
    a full mixed map/array descent (`_descend_to_targets`). A null array is
    replaced with a single stub element so the violation has a row to fire on;
    a null map is stubbed analogously.
    """
    result = copy.deepcopy(row_dict)
    if element_path is not None:

        def _null(target: dict) -> None:
            for name in field_names:
                _set_nested(target, name, None)

        _descend_to_targets(result, coerce(element_path).segments, _null)
        return result
    if map_path is not None:
        target = _map_value_to_mutate(result, map_path)
        if struct_path:
            target = _scaffold_struct_child(target, struct_path)
        for name in field_names:
            _set_nested(target, name, None)
        return result
    if array_path is None:
        for name in field_names:
            _set_nested(result, name, None)
        return result

    arr: list[dict] | None = _get_nested(result, array_path)  # type: ignore[assignment]
    if arr is None:
        stub: dict = {}
        for name in field_names:
            _set_nested(stub, name, None, create=True)
        element = {struct_path: stub} if struct_path else stub
        _set_nested(result, array_path, [element])
    else:
        for element in arr:
            target = (
                _scaffold_struct_child(element, struct_path) if struct_path else element
            )
            for name in field_names:
                _set_nested(target, name, None)
    return result


def _scaffold_struct_child(parent: dict, name: str) -> dict:
    """Return `parent[name]` as a dict, scaffolding `{}` when missing or None."""
    child = parent.get(name)
    if child is None:
        child = {}
        parent[name] = child
    return child


def _map_value_to_mutate(row: dict, map_path: FieldPath | str) -> dict:
    """Return the value model of the map at *map_path*, stubbing if absent.

    A model-level constraint on a `dict[K, Model]` value targets the value
    model. The base row supplies the map's single entry; a missing or empty
    map is stubbed with one entry so the violation has a value to fire on --
    mirroring how a null array is stubbed in `_null_all_named_fields`. The
    map carries exactly one entry (base-row generation emits a single
    key/value pair), so the sole value is unambiguous.
    """
    m = _get_nested(row, map_path)
    if isinstance(m, dict) and m:
        return next(iter(m.values()))
    stub: dict = {}
    _set_nested(row, map_path, {_STUB_MAP_KEY: stub}, create=True)
    return stub


def _descend_to_targets(
    target: Any, segments: tuple[FieldSegment, ...], fn: _Applicator
) -> None:
    """Descend *segments* from *target*, applying *fn* at each reached model dict.

    Walks a full element-relative path that mixes container boundaries:

    - a `StructSegment` navigates one struct field, scaffolding `{}` when
      missing or None;
    - an `ArraySegment` iterates *every* element (a named array is scaffolded
      as `[{}]` when absent; an anonymous one -- the parent element is itself
      the list -- iterates the parent);
    - a `MapSegment` value projection descends the sole entry's value
      (stubbing one entry when a named map is absent).

    A `MapSegment` key projection raises: a model can't sit on the key side.
    Applying to every array element (rather than element 0) mirrors the scalar
    `array_path` helpers, so one invalid element per array is guaranteed.
    """
    if not segments:
        fn(target)
        return
    seg, rest = segments[0], segments[1:]
    if isinstance(seg, StructSegment):
        _descend_to_targets(_scaffold_struct_child(target, seg.name), rest, fn)
    elif isinstance(seg, ArraySegment):
        for element in _element_array(target, seg):
            _descend_to_targets(element, rest, fn)
    elif isinstance(seg, MapSegment):
        _descend_to_targets(_element_map_value(target, seg, rest), rest, fn)
    else:
        raise PathTraversalError(f"unrecognized path segment {seg!r}")


def _element_array(parent: Any, seg: ArraySegment) -> list:
    """Return the list *seg* enters, scaffolding `[{}]` for an absent named array.

    An anonymous segment treats *parent* as the list itself; the parent must
    already be a non-empty list, since there is no field name to scaffold
    against (mirroring `set_at_path`'s anonymous-array handling).
    """
    if seg.is_anonymous:
        if not isinstance(parent, list) or not parent:
            raise PathTraversalError(f"expected non-empty list for anonymous {seg!r}")
        return parent
    arr = parent.get(seg.name) if isinstance(parent, dict) else None
    if arr is None:
        arr = [{}]
        parent[seg.name] = arr
    return arr


def _element_map_value(
    parent: Any, seg: MapSegment, rest: tuple[FieldSegment, ...]
) -> Any:
    """Return the sole value of the map *seg* projects, stubbing when absent.

    A named map absent from *parent* is stubbed with one entry so the descent
    reaches a target; an anonymous map must already be present (the parent
    element is itself the map). A key projection raises -- a model can't sit on
    a map key. The stub is shaped by *rest*, the segments still to descend
    (see `_stub_map_value`): a dict for a `dict[K, Model]` value, a list for a
    `dict[K, list[...]]` value.
    """
    if seg.projection is not MapProjection.VALUE:
        raise PathTraversalError(
            f"model constraint cannot target a map key projection ({seg!r})"
        )
    m = (
        parent
        if seg.is_anonymous
        else (parent.get(seg.name) if isinstance(parent, dict) else None)
    )
    if isinstance(m, dict) and m:
        return next(iter(m.values()))
    if seg.is_anonymous:
        raise PathTraversalError(f"missing anonymous map for {seg!r}")
    stub = _stub_map_value(rest)
    parent[seg.name] = {_STUB_MAP_KEY: stub}
    return stub


def _stub_map_value(rest: tuple[FieldSegment, ...]) -> Any:
    """Build the initial value for a stubbed map entry, shaped to match *rest*.

    A leading anonymous `ArraySegment` in *rest* means the map's value type is
    itself a list (`dict[K, list[X]]`); the stub is `[<next>]`, recursing to
    match a further leading anonymous run (`dict[K, list[list[X]]]`). Any
    other leading segment -- a struct field, a named container, or no segment
    at all -- means the map's value type is a model; the stub is `{}`.
    """
    if rest and isinstance(rest[0], ArraySegment) and rest[0].is_anonymous:
        return [_stub_map_value(rest[1:])]
    return {}


def mutate_require_if(
    row_dict: dict,
    field_names: list[FieldPath | str],
    condition_field: FieldPath | str,
    condition_value: object,
    *,
    negate: bool = False,
    array_path: FieldPath | str | None = None,
    inner_array_path: FieldPath | str | None = None,
    map_path: FieldPath | str | None = None,
    element_path: FieldPath | str | None = None,
) -> dict:
    """Set condition to trigger require_if, then null target fields."""
    result = copy.deepcopy(row_dict)

    def _apply(target: dict) -> None:
        _ensure_condition(target, condition_field, condition_value, negate=negate)
        for name in field_names:
            _set_nested(target, name, None)

    _apply_to_targets(
        result, _apply, array_path, inner_array_path, map_path, element_path
    )
    return result


def mutate_forbid_if(
    row_dict: dict,
    field_names: list[str],
    condition_field: FieldPath | str,
    condition_value: object,
    *,
    negate: bool = False,
    fill_values: dict[str, object] | None = None,
    array_path: FieldPath | str | None = None,
    inner_array_path: FieldPath | str | None = None,
    map_path: FieldPath | str | None = None,
    element_path: FieldPath | str | None = None,
) -> dict:
    """Set condition to trigger forbid_if, ensure target fields are non-null.

    `field_names` are flat scalar field names — model-level forbid_if
    references fields by name on the enclosing model. `fill_values` is
    keyed by the same names.
    """
    result = copy.deepcopy(row_dict)
    fills = fill_values or {}

    def _apply(target: dict) -> None:
        _ensure_condition(target, condition_field, condition_value, negate=negate)
        for name in field_names:
            if _get_nested(target, name) is None:
                _set_nested(target, name, fills.get(name, _SENTINEL))

    _apply_to_targets(
        result, _apply, array_path, inner_array_path, map_path, element_path
    )
    return result


def mutate_unique_items(row_dict: dict, path: FieldPath | str) -> dict:
    """Duplicate the first array element so unique_items fires.

    Supports bracket paths like `"restrictions[].when.mode"` -- enters
    element 0 at each `[]` segment, then duplicates the first element
    of the final array. A terminal run of brackets (e.g. `"hierarchies[]"`,
    or `"grid[][]"` for `list[list[...]]`) targets the array reached by
    descending one extra level per bracket in the run, past the named
    field, and duplicates the first element of the array it lands on.
    """
    result = copy.deepcopy(row_dict)
    segments = coerce(path).segments

    # The terminal run is the last segment if it's a struct, or the maximal
    # trailing run of ArraySegments (one named, then anonymous) otherwise --
    # `hierarchies[][]` parses to two segments but is one bracket run.
    run_start = terminal_run_start(segments)
    run_len = len(segments) - run_start

    parent: Any = _walk_strict(result, path, segments[:run_start])
    last = segments[run_start]
    if not isinstance(parent, dict) or last.name not in parent:
        raise PathTraversalError(f"Missing key '{last.name}' in path '{path}'")

    # When the terminal is an array segment, descend the run's depth in
    # levels of `[0]`. Otherwise the terminal struct already references the
    # list to mutate. The final `container[key]` must itself be a list.
    container: Any
    key: int | str
    if isinstance(last, ArraySegment):
        container, key = _descend_array_run(parent[last.name], run_len, last.name, path)
    else:
        container = parent
        key = last.name
    arr = container[key]
    if not isinstance(arr, list):
        raise PathTraversalError(
            f"Expected list at terminal of path '{path}', got {type(arr).__name__}"
        )
    _duplicate_first(container, key, arr)
    return result


def mutate_map_key(row_dict: dict, path: FieldPath | str, bad_key: object) -> dict:
    """Replace the single map entry's key with *bad_key*, preserving its value.

    *path* is the struct-field path to the map column (e.g. `"names.common"`).
    The base row / scaffold populates the map with one valid entry, so a
    one-entry replacement suffices to trigger the key check. Raises
    `PathTraversalError` when the map is missing or empty.
    """
    _key, value = _single_map_entry(row_dict, path)
    return _replace_map(row_dict, path, {bad_key: value})


def mutate_map_value(row_dict: dict, path: FieldPath | str, bad_value: object) -> dict:
    """Replace the single map entry's value with *bad_value*, preserving its key.

    Mirror of `mutate_map_key` for the value side. Raises
    `PathTraversalError` when the map is missing or empty.
    """
    key, _value = _single_map_entry(row_dict, path)
    return _replace_map(row_dict, path, {key: bad_value})


def _single_map_entry(row_dict: dict, path: FieldPath | str) -> tuple[Any, Any]:
    """Return the `(key, value)` of the sole entry of the map at *path*."""
    m = _get_nested(row_dict, path)
    if not isinstance(m, dict) or not m:
        raise PathTraversalError(f"Missing or empty map at path '{path}'")
    return next(iter(m.items()))


def _replace_map(row_dict: dict, path: FieldPath | str, new_map: dict) -> dict:
    """Return a deep copy of *row_dict* with the map at *path* replaced."""
    result = copy.deepcopy(row_dict)
    _set_nested(result, path, new_map)
    return result


def _walk_strict(
    target: Any, path: FieldPath | str, segments: tuple[FieldSegment, ...] | None = None
) -> Any:
    """Walk *path* without scaffolding, raising on missing or null nodes.

    Raises `PathTraversalError` on missing or null struct intermediates,
    and on empty arrays encountered at array segments (each named
    `ArraySegment` descends one element via a key lookup; each following
    anonymous `ArraySegment` descends one more element with no lookup,
    since the parent element is already the next list). When *segments*
    is provided it overrides the segments derived from *path*; *path*
    still labels error messages.
    """
    if segments is None:
        segments = coerce(path).segments
    for segment in segments:
        if isinstance(segment, ArraySegment) and segment.is_anonymous:
            _require_non_empty_array(target, "[]", path)
            target = target[0]
            continue
        if not isinstance(target, dict) or target.get(segment.name) is None:
            raise PathTraversalError(
                f"Missing or null key '{segment.name}' in path '{path}'"
            )
        target = target[segment.name]
        if isinstance(segment, ArraySegment):
            _require_non_empty_array(target, segment.name, path)
            target = target[0]
    return target


def _descend_array_run(
    arr: list, count: int, name: str, path: FieldPath | str
) -> tuple[Any, int]:
    """Descend *count* levels into nested lists via element 0.

    *count* is 1 for a plain named array terminal, or 1 plus the number of
    trailing anonymous segments for a multi-bracket terminal
    (`hierarchies[][]`). Each level requires a non-empty list; the error
    label for depth `d` is *name* followed by `d` `[]` markers. Returns the
    final `(container, key)` write site so callers can read
    (`container[key]`) or replace (`container[key] = ...`) the innermost
    element.
    """
    container: Any = [arr]
    key = 0
    for depth in range(count):
        inner = container[key]
        _require_non_empty_array(inner, f"{name}{'[]' * depth}", path)
        container, key = inner, 0
    return container, key


def _require_non_empty_array(value: Any, name: str, path: FieldPath | str) -> None:
    """Raise `PathTraversalError` unless *value* is a non-empty list."""
    if not isinstance(value, list) or len(value) == 0:
        raise PathTraversalError(f"Empty or missing array at '{name}' in path '{path}'")


def _duplicate_first(container: Any, key: int | str, arr: list) -> None:
    """Replace `container[key]` with `arr` having its first element duplicated.

    No-op when `arr` is empty. Both elements are deep-copied so callers
    cannot accidentally share state between the duplicates.
    """
    if not arr:
        return
    dup = copy.deepcopy(arr[0])
    container[key] = [dup, copy.deepcopy(dup)] + list(arr[1:])


_Applicator = Callable[[dict], None]


def _apply_to_targets(
    row: dict,
    fn: _Applicator,
    array_path: FieldPath | str | None,
    inner_array_path: FieldPath | str | None,
    map_path: FieldPath | str | None = None,
    element_path: FieldPath | str | None = None,
) -> None:
    """Apply a mutation function to target dicts at the appropriate nesting level.

    Without array or map paths, applies directly to the row. With
    `array_path`, iterates over elements of that array. With both
    `array_path` and `inner_array_path`, iterates over outer elements,
    navigates the inner struct path to a nested array, then iterates those
    elements. With `map_path`, applies to the value model of that map column
    (stubbing one entry when the map is absent). With `element_path`, walks a
    full mixed map/array descent (`_descend_to_targets`).

    Creates stub array elements when the arrays are null so the mutation
    can populate them.
    """
    if element_path is not None:
        _descend_to_targets(row, coerce(element_path).segments, fn)
        return
    if map_path is not None:
        fn(_map_value_to_mutate(row, map_path))
        return
    if array_path is None:
        fn(row)
        return
    outer_arr: list[dict] | None = _get_nested(row, array_path)  # type: ignore[assignment]
    if outer_arr is None:
        outer_stub: dict = {}
        _stub_apply(outer_stub, inner_array_path, fn)
        _set_nested(row, array_path, [outer_stub])
        return
    if inner_array_path is None:
        for element in outer_arr:
            fn(element)
    else:
        for element in outer_arr:
            inner_arr: list[dict] | None = _get_nested(element, inner_array_path)  # type: ignore[assignment]
            if inner_arr is not None:
                for inner_element in inner_arr:
                    fn(inner_element)
            else:
                _stub_apply(element, inner_array_path, fn)


def _stub_apply(
    parent: dict,
    inner_array_path: FieldPath | str | None,
    fn: _Applicator,
) -> None:
    """Build a stub element at `inner_array_path` inside *parent* and run `fn`.

    When `inner_array_path` is None, *parent* itself is the stub that
    `fn` mutates. Otherwise an empty stub is inserted as the sole
    element of `[stub]` at `inner_array_path` inside *parent*
    (scaffolding intermediate dicts), and `fn` mutates the stub.
    """
    if inner_array_path is None:
        fn(parent)
        return
    stub: dict = {}
    fn(stub)
    _set_nested(parent, inner_array_path, [stub], create=True)


def _ensure_condition(
    d: dict,
    condition_field: FieldPath | str,
    condition_value: object,
    *,
    negate: bool,
) -> None:
    """Set condition_field so the constraint condition evaluates to True.

    When *negate* is False, sets the field to *condition_value* (the
    condition is `field == value`).  When True, ensures the field is
    NOT equal to *condition_value* (the condition is `field != value`);
    if it already differs, leaves it alone.
    """
    if negate:
        current = _get_nested(d, condition_field)
        if current == condition_value:
            _set_nested(d, condition_field, f"{_NOT_EQUAL_PREFIX}{condition_value}__")
    else:
        _set_nested(d, condition_field, condition_value)


def _as_direct_path(path: FieldPath | str) -> Direct:
    """Coerce *path* to a `Direct`, rejecting array or map markers.

    The dict-walking helpers operate only on struct fields; an array or
    map-projection marker indicates the caller wanted array-/map-aware
    navigation and picked the wrong helper.
    """
    coerced = coerce(path)
    if not isinstance(coerced, Direct):
        raise ValueError(f"struct-only path expected, got {coerced!r} for {path!r}")
    return coerced


def _set_nested(
    d: dict, path: FieldPath | str, value: object, *, create: bool = False
) -> None:
    """Set a value in a nested dict using a struct-field path.

    When *create* is True, intermediate dicts are created if missing or
    None. When an intermediate is None and *value* is also None, the path
    is already effectively null — returns without error.
    """
    segments = _as_direct_path(path).segments
    target = d
    for segment in segments[:-1]:
        part = segment.name
        if create and (part not in target or target[part] is None):
            target[part] = {}
        child = target.get(part) if isinstance(target, dict) else None
        if child is None:
            if value is None:
                return
            raise PathTraversalError(f"None intermediate at '{part}' in path '{path}'")
        target = child
    target[segments[-1].name] = value


def _get_nested(d: dict, path: FieldPath | str) -> object:
    """Get a value from a nested dict using a struct-field path.

    Returns None when any intermediate key is missing or not a dict.
    """
    target: object = d
    for segment in _as_direct_path(path).segments:
        if not isinstance(target, dict) or segment.name not in target:
            return None
        target = target[segment.name]
    return target
