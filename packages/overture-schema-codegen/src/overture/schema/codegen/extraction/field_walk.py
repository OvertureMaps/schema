"""Generic traversal helpers over `FieldShape` trees.

`shape_children` (one-level child enumeration) and `walk_shape`
(pre-order DFS) cover open-ended traversals; `terminal_of`,
`terminal_scalar`, `list_depth`, `newtype_name`, and `all_constraints`
cover the most common derived views. `ModelRef` and `UnionRef` are
leaves -- the walker does not cross model or union boundaries
automatically; that's a per-consumer decision.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from enum import Enum

from typing_extensions import assert_never

from .field import (
    AnyScalar,
    ArrayOf,
    ConstraintSource,
    FieldShape,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    Scalar,
    UnionRef,
)

__all__ = [
    "all_constraints",
    "enum_source",
    "has_array_layer",
    "list_depth",
    "map_key_value_constraints",
    "newtype_name",
    "shape_children",
    "terminal_model_ref",
    "terminal_of",
    "terminal_primitive",
    "terminal_scalar",
    "walk_shape",
]


def terminal_of(shape: FieldShape) -> FieldShape:
    """Unwrap `ArrayOf` and `NewTypeShape` layers to find the terminal shape.

    Returns the innermost shape that isn't a sequence or NewType wrapper.
    `Scalar`, `ModelRef`, `UnionRef`, and `MapOf` count as terminals.
    """
    while True:
        match shape:
            case ArrayOf(element=inner) | NewTypeShape(inner=inner):
                shape = inner
            case (
                Primitive()
                | LiteralScalar()
                | AnyScalar()
                | ModelRef()
                | UnionRef()
                | MapOf()
            ):
                return shape
            case _:
                assert_never(shape)


def terminal_scalar(shape: FieldShape) -> Scalar | None:
    """Return the terminal `Scalar`, or `None` for non-scalar terminals."""
    terminal = terminal_of(shape)
    return terminal if isinstance(terminal, Scalar) else None


def terminal_primitive(shape: FieldShape) -> Primitive | None:
    """Return the terminal `Primitive`, or `None` for non-primitive terminals.

    Like `terminal_scalar`, but returns `None` for `LiteralScalar` and
    `AnyScalar` — use this when the caller needs `base_type` or
    `source_type`, which only exist on `Primitive`.
    """
    terminal = terminal_of(shape)
    return terminal if isinstance(terminal, Primitive) else None


def terminal_model_ref(shape: FieldShape) -> ModelRef | None:
    """Return the terminal `ModelRef`, or `None` for non-model terminals."""
    terminal = terminal_of(shape)
    return terminal if isinstance(terminal, ModelRef) else None


def enum_source(shape: FieldShape) -> type[Enum] | None:
    """Return the `Enum` class backing a `Primitive`, or `None`.

    Returns the `Enum` subclass stored in `Primitive.source_type` when
    `shape` is a `Primitive` and `source_type` is an `Enum` subclass.
    Returns `None` for every other shape, including wrappers: a
    `NewTypeShape` wrapping an enum-backed `Primitive` returns `None`,
    not the inner enum.

    Parameters
    ----------
    shape
        The shape to inspect.

    Returns
    -------
    type[Enum] or None
        The `Enum` class when `shape` is a `Primitive` backed by one,
        `None` otherwise.
    """
    if not isinstance(shape, Primitive):
        return None
    src = shape.source_type
    if isinstance(src, type) and issubclass(src, Enum):
        return src
    return None


def shape_children(shape: FieldShape) -> Iterator[FieldShape]:
    """Yield direct child shapes within *shape* (one level deep).

    `Scalar`, `ModelRef`, and `UnionRef` have no children.
    """
    match shape:
        case ArrayOf(element=element):
            yield element
        case MapOf(key=key, value=value):
            yield key
            yield value
        case NewTypeShape(inner=inner):
            yield inner
        case Primitive() | LiteralScalar() | AnyScalar() | ModelRef() | UnionRef():
            return
        case _:
            assert_never(shape)


def walk_shape(shape: FieldShape, visit: Callable[[FieldShape], None]) -> None:
    """Pre-order traversal of a `FieldShape` tree.

    Visits *shape*, then descends into each direct child via
    `shape_children`. Stops at `ModelRef` / `UnionRef` -- recursion
    across model boundaries is the caller's choice.
    """
    visit(shape)
    for child in shape_children(shape):
        walk_shape(child, visit)


def list_depth(shape: FieldShape) -> int:
    """Total number of `ArrayOf` layers in *shape*, looking through `NewTypeShape`.

    A NewType wrapping a list counts the same as a list wrapping a
    NewType.
    """
    depth = 0
    cur = shape
    while True:
        match cur:
            case ArrayOf(element=element):
                depth += 1
                cur = element
            case NewTypeShape(inner=inner):
                cur = inner
            case (
                Primitive()
                | LiteralScalar()
                | AnyScalar()
                | ModelRef()
                | UnionRef()
                | MapOf()
            ):
                return depth
            case _:
                assert_never(cur)


def has_array_layer(shape: FieldShape) -> bool:
    """Whether *shape* has any `ArrayOf` layer, looking through `NewTypeShape`.

    Prefer this over `list_depth(shape) > 0` -- callers that only need
    "is this array-shaped" don't need to count layers.
    """
    cur = shape
    while isinstance(cur, NewTypeShape):
        cur = cur.inner
    return isinstance(cur, ArrayOf)


def newtype_name(shape: FieldShape) -> str | None:
    """Return the outermost `NewTypeShape` name, looking through `ArrayOf` layers."""
    cur: FieldShape = shape
    while isinstance(cur, ArrayOf):
        cur = cur.element
    match cur:
        case NewTypeShape(name=name):
            return name
        case (
            Primitive()
            | LiteralScalar()
            | AnyScalar()
            | ModelRef()
            | UnionRef()
            | MapOf()
        ):
            return None
        case _:
            assert_never(cur)


def all_constraints(shape: FieldShape) -> tuple[ConstraintSource, ...]:
    """Concatenate the field's own constraints from every layer of *shape*.

    Walks `NewTypeShape` and `ArrayOf` wrappers to gather constraints
    that apply to this field. Stops at `MapOf` (key/value constraints
    belong to nested key/value shapes, not to the enclosing field) and
    at `ModelRef` / `UnionRef` (which carry no constraints). Constraints
    from outer `ArrayOf` layers appear before constraints from inner
    layers, matching the structural order of the shape tree.
    """
    collected: list[ConstraintSource] = []
    cur = shape
    while True:
        match cur:
            case ArrayOf(element=inner, constraints=cs):
                collected.extend(cs)
                cur = inner
            case NewTypeShape(inner=inner):
                cur = inner
            case (
                Primitive(constraints=cs)
                | LiteralScalar(constraints=cs)
                | AnyScalar(constraints=cs)
            ):
                collected.extend(cs)
                return tuple(collected)
            case MapOf(constraints=cs):
                collected.extend(cs)
                return tuple(collected)
            case ModelRef() | UnionRef():
                return tuple(collected)
            case _:
                assert_never(cur)


def map_key_value_constraints(
    shape: FieldShape,
) -> tuple[tuple[ConstraintSource, ...], tuple[ConstraintSource, ...]]:
    """Return a `MapOf` terminal's (key_constraints, value_constraints), or `((), ())`.

    Looks through `NewTypeShape` / `ArrayOf` wrappers to find a `MapOf`,
    then gathers each side's constraints with `all_constraints`. This
    surfaces per-key and per-value rules that `all_constraints` on the
    enclosing field deliberately stops short of (it treats `MapOf` as a
    terminal). Returns `((), ())` when *shape* has no `MapOf` terminal.
    """
    cur = shape
    while True:
        match cur:
            case NewTypeShape(inner=inner) | ArrayOf(element=inner):
                cur = inner
            case MapOf(key=key, value=value):
                return all_constraints(key), all_constraints(value)
            case _:
                return (), ()
