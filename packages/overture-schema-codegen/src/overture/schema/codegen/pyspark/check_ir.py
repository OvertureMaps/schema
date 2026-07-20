"""Tree-shaped IR for PySpark check expressions.

Sum types describe each check's structural placement:

- `Check.target: FieldPath` -- a `Direct` or `Iterated` locating
  where the descriptor's expression is evaluated. The choice of variant
  signals whether the renderer wraps the expression in an iteration fold
  (`array_check` / `map_values_check` / their nested variants).
- `Guard` -- a single discriminator gate. `Check.guards` is a tuple
  of `Guard`s AND-composed at render time; nested-union gating
  composes one `ColumnGuard` with one `ElementGuard`.

The check_builder produces these types and the renderer consumes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from overture.schema.system.field_path import (
    Direct,
    FieldPath,
    Iterated,
    StructSegment,
)

from .constraint_dispatch import (
    ExpressionDescriptor,
    ForbidIf,
    MinFieldsSet,
    ModelConstraintDescriptor,
    RadioGroup,
    RequireAnyOf,
    RequireAnyTrue,
    RequireIf,
    require_field_eq,
)

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


def _top_level(name: str) -> str:
    """Strip a dotted field name to its top-level column."""
    return name.split(".", 1)[0]


def _path_top_column(path: FieldPath) -> str | None:
    """Top-level row column for a `FieldPath`, or `None` for an empty `Direct`.

    Collapses dotted struct navigation to its first segment -- the granularity
    at which `validate_model` detects column absence. `Iterated.outer_column`
    may be dotted when the iterated column is nested inside a struct (e.g.
    `names.rules`); this strips to `names`.
    """
    match path:
        case Direct(segments=(StructSegment(name=first), *_)):
            return first
        case Direct():
            return None
        case Iterated():
            return _top_level(path.outer_column)
        case _:
            raise TypeError(f"Unhandled FieldPath variant: {type(path).__name__}")


@dataclass(frozen=True, slots=True)
class Check:
    """A field-level validation check."""

    descriptors: tuple[ExpressionDescriptor, ...]
    target: FieldPath
    guards: tuple[Guard, ...] = ()

    @property
    def read_columns(self) -> frozenset[str]:
        """Top-level row columns this check's expression dereferences.

        Includes the target's outermost column, any `ColumnGuard` discriminator
        (rendered as `F.col(...)`), and any descriptor gate on a `Direct`
        target (rendered as `F.col("{gate}").isNotNull()`). `ElementGuard`
        discriminators are excluded -- they reference `el[...]`, an
        element-relative accessor, not a row-level column. Descriptor gates on
        `Iterated` targets are also excluded -- they are applied element-relatively
        via `element_relative_gate`.
        """
        cols: set[str] = set()
        top = _path_top_column(self.target)
        if top is not None:
            cols.add(top)
        for guard in self.guards:
            match guard:
                case ColumnGuard(discriminator=d):
                    cols.add(d)
                case ElementGuard():
                    pass  # element-relative: not a row-level read
                case _:
                    raise TypeError(f"Unhandled Guard variant: {type(guard).__name__}")
        if isinstance(self.target, Direct):
            for desc in self.descriptors:
                if desc.gate is not None:
                    gate_col = _path_top_column(desc.gate)
                    if gate_col is not None:
                        cols.add(gate_col)
        return frozenset(cols)


@dataclass(frozen=True, slots=True)
class ModelCheck:
    """A model-level validation check (cross-field constraint).

    `target` locates the model the constraint applies to: an empty
    `Direct()` for row-root constraints, or an `Iterated` when the
    constrained model is reached by iterating one or more arrays or maps.
    The default `Direct()` makes the row-root case ergonomic at
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
    `gate` is always applied element-relatively for array targets and
    must be `None` for scalar targets, so it never contributes a
    top-level row column to `read_columns`.
    """

    descriptor: ModelConstraintDescriptor
    target: FieldPath = Direct()
    arm: str | None = None
    gate: FieldPath | None = None

    @property
    def read_columns(self) -> frozenset[str]:
        """Top-level row columns this model check's expression dereferences.

        For row-root constraints (`Direct` target): all `field_names` from
        the constraint (collapsed to top-level column) and, for `RequireIf`/
        `ForbidIf`, the condition field (both rendered as `F.col(...)`).

        For `Iterated` (array/map) targets: only the outermost container
        column is a row-level read (`array_check("col", ...)` /
        `map_values_check("col", ...)`). The `field_names` and condition field
        are accessed as element-relative `el[...]` / `inner[...]` accessors
        inside the lambda -- not as `F.col(...)` -- so they do not contribute
        top-level column reads.

        `gate` is excluded: for `Iterated` targets it is element-relative; for
        `Direct` targets the renderer asserts it is `None`. The `arm` field
        carries no column information.
        """
        cols: set[str] = set()
        desc = self.descriptor
        # Iterated targets wrap everything in array_check/map_values_check;
        # field references inside the lambda are element-relative, not row-level.
        # Only the container column itself is a top-level read.
        if isinstance(self.target, Iterated):
            container_col = _path_top_column(self.target)
            if container_col is not None:
                cols.add(container_col)
            return frozenset(cols)
        # Row-root target: field_names and condition field render as F.col(...).
        match desc:
            case (
                RequireAnyOf(field_names=names)
                | RadioGroup(field_names=names)
                | RequireAnyTrue(field_names=names)
                | MinFieldsSet(field_names=names)
            ):
                for name in names:
                    cols.add(_top_level(name))
            case (
                RequireIf(field_names=names, condition=cond)
                | ForbidIf(field_names=names, condition=cond)
            ):
                for name in names:
                    cols.add(_top_level(name))
                cols.add(require_field_eq(cond).field_name)
            case _:
                raise TypeError(
                    f"Unhandled ModelConstraintDescriptor variant: {type(desc).__name__}"
                )
        return frozenset(cols)
