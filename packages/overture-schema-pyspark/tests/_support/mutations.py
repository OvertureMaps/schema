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
    ArrayPath,
    ArraySegment,
    FieldPath,
    PathSegment,
    ScalarPath,
    coerce,
)

from .helpers import PathTraversalError

_SENTINEL = "__FORBIDDEN_PRESENT__"
_NOT_EQUAL_PREFIX = "__NOT_"


def mutate_require_any_of(
    row_dict: dict,
    field_names: list[FieldPath | str],
    *,
    array_path: FieldPath | str | None = None,
    struct_path: str | None = None,
) -> dict:
    """Null every named field so `require_any_of` fires.

    Parameters
    ----------
    array_path
        Array column the constrained model lives inside. When None, the
        fields live at the row root.
    struct_path
        Optional single intermediate struct field between the array
        element and the target fields.

    See `_null_all_named_fields` for the full nesting semantics.
    """
    return _null_all_named_fields(
        row_dict, field_names, array_path=array_path, struct_path=struct_path
    )


def mutate_radio_group(row_dict: dict, field_names: list[FieldPath | str]) -> dict:
    """Set first two fields to True so radio_group fires."""
    result = copy.deepcopy(row_dict)
    for name in field_names[:2]:
        _set_nested(result, name, True)
    return result


def mutate_min_fields_set(
    row_dict: dict,
    field_names: list[FieldPath | str],
    *,
    array_path: FieldPath | str | None = None,
    struct_path: str | None = None,
) -> dict:
    """Null every named field so `min_fields_set(N)` fires (0 < N).

    The descriptor enumerates every field of the constrained model, so
    nulling all of them drops the non-null count to zero -- below any
    positive `count`. Nulling required fields incidentally trips their
    `check_required` checks; the conformance test only asserts the
    expected violation is present, so the extra failures don't matter.

    `array_path` / `struct_path` mirror `mutate_require_any_of` for the
    case where the constrained model is reached through array iteration
    (and optionally one intermediate struct field).
    """
    return _null_all_named_fields(
        row_dict, field_names, array_path=array_path, struct_path=struct_path
    )


def _null_all_named_fields(
    row_dict: dict,
    field_names: list[FieldPath | str],
    *,
    array_path: FieldPath | str | None,
    struct_path: str | None,
) -> dict:
    """Return a deep copy of *row_dict* with every named field set to None.

    Without *array_path*, the fields live at the row root. With *array_path*,
    the fields live inside elements of that array column; *struct_path*
    names an optional single intermediate struct field between the array
    element and the target fields. A null array is replaced with a single
    stub element so the violation has a row to fire on.
    """
    result = copy.deepcopy(row_dict)
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
            if struct_path:
                target = element.get(struct_path)
                if target is None:
                    target = {}
                    element[struct_path] = target
            else:
                target = element
            for name in field_names:
                _set_nested(target, name, None)
    return result


def mutate_require_if(
    row_dict: dict,
    field_names: list[FieldPath | str],
    condition_field: FieldPath | str,
    condition_value: object,
    *,
    negate: bool = False,
    array_path: FieldPath | str | None = None,
    inner_array_path: FieldPath | str | None = None,
) -> dict:
    """Set condition to trigger require_if, then null target fields."""
    result = copy.deepcopy(row_dict)

    def _apply(target: dict) -> None:
        _ensure_condition(target, condition_field, condition_value, negate=negate)
        for name in field_names:
            _set_nested(target, name, None)

    _apply_to_targets(result, _apply, array_path, inner_array_path)
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

    _apply_to_targets(result, _apply, array_path, inner_array_path)
    return result


def mutate_unique_items(row_dict: dict, path: FieldPath | str) -> dict:
    """Duplicate the first array element so unique_items fires.

    Supports bracket paths like `"restrictions[].when.mode"` -- enters
    element 0 at each `[]` segment, then duplicates the first element
    of the final array. A terminal `[]` (e.g. `"hierarchies[]"`)
    targets the inner array at element 0 of the named field -- the
    walker descends one extra level per bracket on the terminal
    segment and duplicates the first element of the array it lands on.
    """
    result = copy.deepcopy(row_dict)
    segments = coerce(path).segments

    parent: Any = _walk_strict(result, segments[:-1], path)
    last = segments[-1]
    if not isinstance(parent, dict) or last.name not in parent:
        raise PathTraversalError(f"Missing key '{last.name}' in path '{path}'")

    # When the terminal is an array segment, descend `iter_count` levels of
    # `[0]`. Otherwise the terminal struct already references the list to
    # mutate. The final `container[key]` must itself be a list.
    container: Any = parent
    key: int | str = last.name
    iter_count = last.iter_count if isinstance(last, ArraySegment) else 0
    for depth in range(iter_count):
        inner = container[key]
        _require_non_empty_array(inner, f"{last.name}{'[]' * depth}", path)
        container, key = inner, 0
    arr = container[key]
    if not isinstance(arr, list):
        raise PathTraversalError(
            f"Expected list at terminal of path '{path}', got {type(arr).__name__}"
        )
    _duplicate_first(container, key, arr)
    return result


def _walk_strict(
    target: Any, segments: tuple[PathSegment, ...], path: FieldPath | str
) -> Any:
    """Walk segments without scaffolding.

    Raises `PathTraversalError` on missing or null struct intermediates,
    and on empty arrays encountered at array intermediates (each `[]` in
    a segment's `iter_count` descends one element, which requires a
    non-empty list).
    """
    for segment in segments:
        if not isinstance(target, dict) or target.get(segment.name) is None:
            raise PathTraversalError(
                f"Missing or null key '{segment.name}' in path '{path}'"
            )
        target = target[segment.name]
        if isinstance(segment, ArraySegment):
            for _ in range(segment.iter_count):
                _require_non_empty_array(target, segment.name, path)
                target = target[0]
    return target


def _require_non_empty_array(value: Any, name: str, path: FieldPath | str) -> None:
    """Raise PathTraversalError unless *value* is a non-empty list."""
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
) -> None:
    """Apply a mutation function to target dicts at the appropriate nesting level.

    Without array paths, applies directly to the row. With `array_path`,
    iterates over elements of that array. With both `array_path` and
    `inner_array_path`, iterates over outer elements, navigates the
    inner struct path to a nested array, then iterates those elements.

    Creates stub array elements when the arrays are null so the mutation
    can populate them.
    """
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


def _as_scalar_path(path: FieldPath | str) -> ScalarPath:
    """Coerce *path* to a ScalarPath, rejecting any array markers.

    The dict-walking helpers operate only on struct fields; an array
    marker indicates the caller wanted array-aware navigation and picked
    the wrong helper.
    """
    coerced = coerce(path)
    if isinstance(coerced, ArrayPath):
        raise ValueError(f"struct-only path expected, got array segment in {path!r}")
    return coerced


def _set_nested(
    d: dict, path: FieldPath | str, value: object, *, create: bool = False
) -> None:
    """Set a value in a nested dict using a struct-field path.

    When *create* is True, intermediate dicts are created if missing or
    None. When an intermediate is None and *value* is also None, the path
    is already effectively null — returns without error.
    """
    segments = _as_scalar_path(path).segments
    target = d
    for segment in segments[:-1]:
        part = segment.name
        if create and (part not in target or target[part] is None):
            target[part] = {}
        child = target.get(part) if isinstance(target, dict) else None
        if child is None:
            if value is None:
                return
            raise TypeError(f"None intermediate at '{part}' in path '{path}'")
        target = child
    target[segments[-1].name] = value


def _get_nested(d: dict, path: FieldPath | str) -> object:
    """Get a value from a nested dict using a struct-field path.

    Returns None when any intermediate key is missing.
    """
    target: object = d
    for segment in _as_scalar_path(path).segments:
        if not isinstance(target, dict) or segment.name not in target:
            return None
        target = target[segment.name]
    return target
