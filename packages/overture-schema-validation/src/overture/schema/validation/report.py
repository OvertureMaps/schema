"""Validation execution report."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .ir import Severity


class RuleResult(BaseModel):
    """A single rule violation for one row."""

    name: str
    violating_id: Any
    severity: Severity


class ValidationReport(BaseModel):
    """Aggregate report for a dataset validation run."""

    dataset: str
    results: list[RuleResult]
