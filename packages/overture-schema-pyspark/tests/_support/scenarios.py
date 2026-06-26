"""Scenario dataclass for generated conformance tests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Scenario:
    """A test scenario: a mutation that should produce a specific violation.

    Parameters
    ----------
    id
        Human-readable scenario identifier, e.g. `"building::id:required"`.
    scaffold
        Dict merged onto the base row before mutation to provide valid values
        for fields the base row lacks (e.g. array elements for nested paths).
    mutate
        Callable applied to `deep_merge(base_row, scaffold)` to produce the
        invalid row. Must return a new dict; must not mutate its argument.
    expected_field
        Field name expected in the violation output.
    expected_check
        Check name expected in the violation output.
    """

    id: str
    scaffold: dict[str, Any]
    mutate: Callable[[dict], dict]
    expected_field: str
    expected_check: str
    valid_scaffold: dict[str, Any] | None = None
    """Override scaffold for the `::valid` row, when it must differ from `scaffold`.

    The harness builds the `::valid` row from `scaffold` by default (merged
    onto the base row, no mutation), which already places a constraint-valid
    value at the check's target. Set this only when the valid row needs a
    *different* value there -- e.g. an `X | Literal[c]` field, where it seeds
    the literal alternative `c` to prove the check accepts it, distinct from
    the synthesized `X` value the mutation scaffold carries.
    """
