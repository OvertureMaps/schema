"""Validation IR data types for YAML serialization."""

from __future__ import annotations

from dataclasses import dataclass

import yaml

__all__ = ["ConditionIR", "DatasetIR", "RuleIR", "ValidationIR"]


@dataclass(frozen=True, slots=True)
class ConditionIR:
    """Guard predicate for conditional rules."""

    column: str
    check: str
    value: object | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict, omitting None fields."""
        d: dict[str, object] = {"column": self.column, "check": self.check}
        if self.value is not None:
            d["value"] = self.value
        return d


@dataclass(frozen=True, slots=True)
class RuleIR:
    """Single validation rule."""

    name: str
    check: str
    severity: str
    column: str | None = None
    columns: list[str] | None = None
    value: object | None = None
    list_columns: list[str] | None = None
    when: ConditionIR | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict, omitting None fields."""
        d: dict[str, object] = {"name": self.name}
        if self.column is not None:
            d["column"] = self.column
        if self.columns is not None:
            d["columns"] = self.columns
        d["check"] = self.check
        if self.value is not None:
            d["value"] = self.value
        if self.list_columns is not None:
            d["list_columns"] = self.list_columns
        if self.when is not None:
            d["when"] = self.when.to_dict()
        d["severity"] = self.severity
        return d


@dataclass(frozen=True, slots=True)
class DatasetIR:
    """Validation rules for one feature type."""

    name: str
    source_model: str
    id_column: str
    rules: list[RuleIR]

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "name": self.name,
            "source_model": self.source_model,
            "id_column": self.id_column,
            "rules": [r.to_dict() for r in self.rules],
        }


@dataclass(frozen=True, slots=True)
class ValidationIR:
    """Full validation IR envelope."""

    datasets: list[DatasetIR]
    version: str = "1"

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        data = {
            "version": self.version,
            "datasets": [ds.to_dict() for ds in self.datasets],
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
