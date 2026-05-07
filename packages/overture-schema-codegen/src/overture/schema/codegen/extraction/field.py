"""Tree-shaped IR for model field types.

`FieldShape` is a discriminated union -- `Primitive`, `LiteralScalar`,
`AnyScalar`, `ModelRef`, `UnionRef`, `ArrayOf`, `MapOf`, `NewTypeShape`
-- nested to describe arbitrary list / dict / NewType wrapping. Each
variant carries its own constraints (where meaningful), and walkers
encounter each constraint at the layer it targets.

The three terminal scalar variants (`Primitive`, `LiteralScalar`,
`AnyScalar`) are grouped under the `Scalar` type alias for consumers
that only need to ask "is this a leaf?".

`NewTypeShape` wraps an inner shape, so its position relative to
`ArrayOf` is structural: `NewTypeShape(inner=ArrayOf(...))` is a
NewType over `list[X]`, while `ArrayOf(element=NewTypeShape(...))`
is a list of NewType-wrapped values. Consumers pattern-match on
shape to distinguish the two.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from .specs import ModelSpec, UnionSpec

__all__ = [
    "AnyScalar",
    "ArrayOf",
    "ConstraintSource",
    "FieldShape",
    "LiteralScalar",
    "MapOf",
    "ModelRef",
    "NewTypeShape",
    "Primitive",
    "Scalar",
    "UnionRef",
]


@dataclass(frozen=True, slots=True)
class ConstraintSource:
    """A constraint paired with the NewType that contributed it.

    `source_ref` and `source_name` identify the NewType that declared
    the constraint; both are `None` for constraints contributed directly
    on a field annotation rather than through a NewType. `constraint`
    is the raw metadata object from `Annotated[..., constraint]`.
    """

    source_ref: object | None
    source_name: str | None
    constraint: object


@dataclass(frozen=True, slots=True)
class Primitive:
    """Terminal type with a registry lookup key.

    Covers primitives (`int32`, `str`), enums, Pydantic built-ins
    (`HttpUrl`, `EmailStr`), and `BaseModel` subclasses that weren't
    resolved to a `ModelRef` (e.g. when no `model_resolver` was
    supplied).
    """

    base_type: str
    source_type: type | None = None
    constraints: tuple[ConstraintSource, ...] = ()


@dataclass(frozen=True, slots=True)
class LiteralScalar:
    """`Literal[X, ...]` terminal."""

    values: tuple[object, ...]
    constraints: tuple[ConstraintSource, ...] = ()


@dataclass(frozen=True, slots=True)
class AnyScalar:
    """`typing.Any` terminal."""

    constraints: tuple[ConstraintSource, ...] = ()


Scalar: TypeAlias = Primitive | LiteralScalar | AnyScalar
"""Terminal shape: a value that doesn't wrap another shape.

Consumers that just need "is this a leaf?" check `isinstance(x, Scalar)`;
consumers that need terminal-specific data narrow to a variant.
"""


@dataclass(frozen=True, slots=True)
class ModelRef:
    """Reference to a Pydantic sub-model.

    `starts_cycle` marks the back-edge of a cycle in the model graph;
    consumers that recurse into models must stop at cycle starts.
    """

    model: ModelSpec
    starts_cycle: bool = False


@dataclass(frozen=True, slots=True)
class UnionRef:
    """Reference to a discriminated union of models."""

    union: UnionSpec


@dataclass(frozen=True, slots=True)
class ArrayOf:
    """Sequence of values sharing a single element shape.

    Nested arrays are nested `ArrayOf` instances; there is no numeric
    depth field. `constraints` carries array-level validation rules
    (length, uniqueness). Per-element constraints live on `element`
    and its descendants.
    """

    element: FieldShape
    constraints: tuple[ConstraintSource, ...] = ()


@dataclass(frozen=True, slots=True)
class MapOf:
    """Mapping from a key shape to a value shape.

    `constraints` carries map-level validation rules. Per-key and
    per-value constraints live on `key` / `value` respectively.
    """

    key: FieldShape
    value: FieldShape
    constraints: tuple[ConstraintSource, ...] = ()


@dataclass(frozen=True, slots=True)
class NewTypeShape:
    """A NewType wrapper around an inner shape.

    Position relative to other wrappers is meaningful:
    `NewTypeShape(inner=ArrayOf(...))` is a NewType over `list[X]`;
    `ArrayOf(element=NewTypeShape(...))` is a list of NewType-wrapped
    values. Consumers distinguish the two by pattern, not a numeric
    offset.

    Constraints contributed by the NewType chain attach to the
    `Scalar` / `ArrayOf` / `MapOf` layer they target, not to the
    wrapper itself. `name` and `ref` identify the NewType for linking
    without owning constraint state.
    """

    name: str
    ref: object
    inner: FieldShape


FieldShape: TypeAlias = (
    Primitive
    | LiteralScalar
    | AnyScalar
    | ModelRef
    | UnionRef
    | ArrayOf
    | MapOf
    | NewTypeShape
)
