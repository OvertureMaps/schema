"""Internal constraint recording a union's literal alternatives.

A field annotated `X | Literal[c, ...]` validates as "the concrete arm `X`'s
checks pass OR the value is one of `c, ...`". `type_analyzer._peel_union` keeps
the concrete arm as the field's shape (so downstream consumers still see a
`Primitive` / `NewTypeShape` rather than a union of scalar-and-literal) and
records the dropped literal values in this constraint on that shape's layer.

Consumers read it to let those literal values bypass the concrete arm's
constraints: the PySpark dispatch emits a value-exact bypass, and the markdown
renderer notes the accepted literals. Codegen-internal -- schema authors write
the plain `X | Literal[c]` union; nothing constructs this class directly.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["LiteralAlternatives"]


@dataclass(frozen=True, slots=True)
class LiteralAlternatives:
    """Literal values a union field accepts alongside its concrete arm."""

    values: tuple[object, ...]
