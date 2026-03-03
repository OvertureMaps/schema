"""Validation execution report."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .ir import Severity


class RuleResult(BaseModel):
    """Result of evaluating a single validation rule."""

    rule_name: str
    description: str | None = None
    violating_ids: list[Any] = []
    violation_count: int = 0
    severity: Severity


class ValidationReport(BaseModel):
    """Aggregate report for a dataset validation run."""

    dataset: str
    total_rows: int
    results: list[RuleResult]
