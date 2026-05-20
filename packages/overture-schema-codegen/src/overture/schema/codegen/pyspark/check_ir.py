"""Tree-shaped IR for PySpark check expressions.

Sum types describe each check's structural placement:

- `Check.target: FieldPath` -- a `ScalarPath` or `ArrayPath` locating
  where the descriptor's expression is evaluated. The choice of variant
  signals whether the renderer wraps the expression in `array_check` /
  `nested_array_check`.
- `Guard` -- a single discriminator gate. `Check.guards` is a tuple
  of `Guard`s AND-composed at render time; nested-union gating
  composes one `ColumnGuard` with one `ElementGuard`.

The check_builder produces these types and the renderer consumes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from overture.schema.system.field_path import FieldPath, ScalarPath

from .constraint_dispatch import ExpressionDescriptor, ModelConstraintDescriptor

__all__ = [
    "Check",
    "ColumnGuard",
    "ElementGuard",
    "Guard",
    "ModelCheck",
]


@dataclass(frozen=True, slots=True)
class ColumnGuard:
    """Discriminator gate where the discriminator is a top-level row column."""

    discriminator: str
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ElementGuard:
    """Discriminator gate where the discriminator is a struct field inside an array element."""

    discriminator: str
    values: tuple[str, ...]


Guard: TypeAlias = ColumnGuard | ElementGuard


@dataclass(frozen=True, slots=True)
class Check:
    """A field-level validation check."""

    descriptors: tuple[ExpressionDescriptor, ...]
    target: FieldPath
    guards: tuple[Guard, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelCheck:
    """A model-level validation check (cross-field constraint).

    `target` locates the model the constraint applies to: an empty
    `ScalarPath()` for row-root constraints, or an `ArrayPath` when the
    constrained model is reached by iterating one or more arrays. The
    default `ScalarPath()` makes the row-root case ergonomic at
    construction sites and is the common case; `Check.target` has no
    sensible default and is required.

    `arm` records the discriminator value of the union member that
    contributed the constraint, or `None` when the constraint applies to
    every arm. The test renderer filters per-arm test modules by this
    value. Constraints discovered through a variant-specific field's
    sub-model or sub-union inherit the contributing outer arm, so they
    land only in that arm's test module.

    `gate` is the optional-ancestor path that must be non-null for the
    constraint to apply. Set when the constrained model is reached via
    an optional field (`field: Model | None`). The renderer wraps the
    constraint expression in `F.when(<accessor>.isNotNull(), ...)` so
    the check is skipped when the optional model is absent (NULL).
    """

    descriptor: ModelConstraintDescriptor
    target: FieldPath = ScalarPath()
    arm: str | None = None
    gate: FieldPath | None = None
