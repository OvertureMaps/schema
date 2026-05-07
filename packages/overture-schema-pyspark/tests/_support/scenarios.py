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
