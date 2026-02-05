"""
Format validators for schema validation against different file types.

Each validator takes a file and a Pydantic model class and returns a SchemaDiff
indicating any mismatches.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Schema diff types
# ---------------------------------------------------------------------------


@dataclass
class FieldDiff:
    """A single difference found when comparing two schema fields."""

    path: str
    kind: str  # "missing", "extra", "type_mismatch", "nullability"
    expected: str | None = None
    actual: str | None = None


@dataclass
class SchemaDiff:
    """Complete result of comparing expected vs actual schema."""

    missing_fields: list[FieldDiff] = field(default_factory=list)
    extra_fields: list[FieldDiff] = field(default_factory=list)
    type_mismatches: list[FieldDiff] = field(default_factory=list)
    nullability_issues: list[FieldDiff] = field(default_factory=list)

    @property
    def is_compatible(self) -> bool:
        """True if no missing fields, type mismatches, or nullability issues."""
        return (
            not self.missing_fields
            and not self.type_mismatches
            and not self.nullability_issues
        )

    @property
    def is_exact_match(self) -> bool:
        """True if compatible and no extra fields."""
        return self.is_compatible and not self.extra_fields

    def passed(self, *, strict: bool = False, skip: set[str] | None = None) -> bool:
        """Check if the diff passes with optional skipped categories.

        Parameters
        ----------
        strict : bool
            If True, extra fields also cause failure.
        skip : set[str] | None
            Categories to ignore: "missing", "extra", "type-mismatch", "nullability".
        """
        skip = skip or set()
        checks = {
            "missing": self.missing_fields,
            "type-mismatch": self.type_mismatches,
            "nullability": self.nullability_issues,
        }
        if strict:
            checks["extra"] = self.extra_fields
        return all(
            not diffs for name, diffs in checks.items() if name not in skip
        )

    def to_rows(self) -> list[dict[str, str | None]]:
        """Flatten all diffs into a list of row dicts for tabular export."""
        return [
            {"path": d.path, "kind": d.kind, "expected": d.expected, "actual": d.actual}
            for d in (
                self.missing_fields + self.extra_fields
                + self.type_mismatches + self.nullability_issues
            )
        ]


# ---------------------------------------------------------------------------
# Format validators
# ---------------------------------------------------------------------------


class FormatValidator(ABC):
    """Base class for format-specific schema validators."""

    @abstractmethod
    def validate(
        self,
        path: Path,
        model: type["BaseModel"],
        *,
        ignore_fields: set[str] | None = None,
    ) -> SchemaDiff:
        """
        Validate a file's schema against a Pydantic model.

        Parameters
        ----------
        path : Path
            Path to the file to validate
        model : type[BaseModel]
            Pydantic model class defining the expected schema
        ignore_fields : set[str] | None
            Field names to skip during comparison

        Returns
        -------
        SchemaDiff
            Differences between expected and actual schema
        """
        pass

    @classmethod
    def for_file(cls, path: Path) -> "FormatValidator":
        """Select appropriate validator based on file extension."""
        validators: dict[str, type[FormatValidator]] = {
            ".parquet": ParquetValidator,
        }
        suffix = path.suffix.lower()
        if suffix not in validators:
            supported = ", ".join(sorted(validators.keys()))
            raise ValueError(
                f"Unsupported file format '{suffix}'. Supported: {supported}"
            )
        return validators[suffix]()


class ParquetValidator(FormatValidator):
    """Validator for Parquet files."""

    def validate(
        self,
        path: Path,
        model: type["BaseModel"],
        *,
        ignore_fields: set[str] | None = None,
    ) -> SchemaDiff:
        import pyarrow.parquet as pq

        from .arrow_schema import compare_schemas, pydantic_model_to_arrow_schema

        # Convert model to Arrow schema
        expected_schema = pydantic_model_to_arrow_schema(model)

        # Read actual schema from file
        actual_schema = pq.read_schema(path)

        # Compare
        return compare_schemas(expected_schema, actual_schema, ignore_fields=ignore_fields)
