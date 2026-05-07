"""Internal typed length-constraint classes.

`annotated_types.MaxLen` and `annotated_types.MinLen` are polysemous:
`MaxLen(10)` on a `str` constrains character count, while `MaxLen(10)`
on a `list[X]` constrains cardinality. The codegen extractor splits
them by attachment layer so each variant carries its own dispatch:
`ArrayMinLen` / `ArrayMaxLen` for `ArrayOf` layers, `ScalarMinLen` /
`ScalarMaxLen` for scalar layers.

These are codegen-internal classes -- Pydantic users continue to write
`Annotated[X, MinLen(n)]` in their schemas; the wrapping happens inside
`type_analyzer.attach_constraints` when the constraint reaches its
target layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from annotated_types import MaxLen, MinLen

__all__ = [
    "ArrayMaxLen",
    "ArrayMinLen",
    "ScalarMaxLen",
    "ScalarMinLen",
]


@dataclass(frozen=True)
class ArrayMinLen(MinLen):
    """Cardinality lower bound for an `ArrayOf` layer."""


@dataclass(frozen=True)
class ArrayMaxLen(MaxLen):
    """Cardinality upper bound for an `ArrayOf` layer."""


@dataclass(frozen=True)
class ScalarMinLen(MinLen):
    """Character-count lower bound for a scalar layer."""


@dataclass(frozen=True)
class ScalarMaxLen(MaxLen):
    """Character-count upper bound for a scalar layer."""
