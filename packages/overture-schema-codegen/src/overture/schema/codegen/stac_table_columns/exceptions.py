"""Typed record of everything the `table:columns` emit could not carry.

`flatten-collision` is the kind only a flattening target produces: two union
arms contributing the same column name, where a columnar sink keeps one and the
other's meaning is gone with no trace in the output. `unrepresentable-in-pydantic`
runs the other way -- the target asks for something Pydantic has no way to
declare, so the gap is a possible Overture Schema feature rather than a defect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["Kind", "TableColumnsGap", "TableColumnsUnrepresentable"]

Kind = Literal[
    "ir-gap",
    "target-gap",
    "target-dialect",
    "flatten-collision",
    "unrepresentable-in-pydantic",
    "renderer-gap",
]


@dataclass(frozen=True, slots=True)
class TableColumnsGap:
    """One capability that did not survive the emit.

    `path` locates it in the emitted document, `capability` names what was lost
    in the vocabulary of whichever side owns the loss, and `detail` carries the
    mechanism. Classification is by mechanism, not by keyword.
    """

    model: str
    path: str
    kind: Kind
    capability: str
    detail: str


class TableColumnsUnrepresentable(Exception):
    """Raised in strict mode, or when the renderer cannot proceed at all."""

    def __init__(self, gaps: tuple[TableColumnsGap, ...]) -> None:
        self.gaps = gaps
        head = gaps[0]
        super().__init__(
            f"{head.model}{head.path}: {head.capability} ({head.kind}) -- {head.detail}"
            + (f" [+{len(gaps) - 1} more]" if len(gaps) > 1 else "")
        )
