"""Validation rule intermediate representation (IR)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator
from typing_extensions import Self


class CheckType(str, Enum):
    """Closed set of check types that all backends must support."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    NOT_NULL = "not_null"
    IS_NULL = "is_null"
    UNIQUE = "unique"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    IS_TYPE = "is_type"
    COLUMN_LT = "column_lt"
    COLUMN_LTE = "column_lte"
    COLUMN_EQ = "column_eq"
    GEOMETRY_TYPE = "geometry_type"
    EXACTLY_ONE_OF = "exactly_one_of"
    ANY_OF = "any_of"


class Severity(str, Enum):
    """Severity level of a validation rule."""

    ERROR = "error"
    WARNING = "warning"


# Checks that require no value
_NO_VALUE_CHECKS: frozenset[CheckType] = frozenset(
    {
        CheckType.NOT_NULL,
        CheckType.IS_NULL,
        CheckType.UNIQUE,
        CheckType.EXACTLY_ONE_OF,
        CheckType.ANY_OF,
    }
)

# Checks that require other_column
_COLUMN_CHECKS: frozenset[CheckType] = frozenset(
    {
        CheckType.COLUMN_LT,
        CheckType.COLUMN_LTE,
        CheckType.COLUMN_EQ,
    }
)

# Checks that use columns (list) instead of column (single)
_MULTI_FIELD_CHECKS: frozenset[CheckType] = frozenset(
    {
        CheckType.EXACTLY_ONE_OF,
        CheckType.ANY_OF,
    }
)

# Checks that allow the each_item modifier
_EACH_ITEM_CHECKS: frozenset[CheckType] = frozenset(
    {
        CheckType.GT,
        CheckType.GTE,
        CheckType.LT,
        CheckType.LTE,
        CheckType.EQ,
        CheckType.NEQ,
        CheckType.BETWEEN,
        CheckType.IN,
        CheckType.NOT_IN,
        CheckType.NOT_NULL,
        CheckType.IS_NULL,
        CheckType.PATTERN,
        CheckType.IS_TYPE,
    }
)

# Checks allowed inside a when condition
_WHEN_CHECKS: frozenset[CheckType] = frozenset(
    {
        CheckType.GT,
        CheckType.GTE,
        CheckType.LT,
        CheckType.LTE,
        CheckType.EQ,
        CheckType.NEQ,
        CheckType.BETWEEN,
        CheckType.IN,
        CheckType.NOT_IN,
        CheckType.NOT_NULL,
        CheckType.IS_NULL,
        CheckType.PATTERN,
        CheckType.IS_TYPE,
    }
)


class Condition(BaseModel):
    """Single predicate guard for conditional rule evaluation."""

    column: str
    check: CheckType
    value: Any = None

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        if self.check not in _WHEN_CHECKS:
            msg = (
                f"check '{self.check.value}' is not allowed "
                f"inside a when condition"
            )
            raise ValueError(msg)
        if self.check not in _NO_VALUE_CHECKS and self.value is None:
            msg = f"check '{self.check.value}' requires a value"
            raise ValueError(msg)
        return self


class Rule(BaseModel):
    """A single validation rule in the IR."""

    name: str
    column: str | None = None
    columns: list[str] | None = None
    check: CheckType
    value: Any = None
    other_column: str | None = None
    each_item: bool | None = None
    when: Condition | None = None
    severity: Severity
    description: str | None = None

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        is_multi = self.check in _MULTI_FIELD_CHECKS
        is_col_cmp = self.check in _COLUMN_CHECKS

        # column vs columns mutual exclusivity
        if is_multi:
            if self.column is not None:
                msg = (
                    f"check '{self.check.value}' uses 'columns', "
                    f"not 'column'"
                )
                raise ValueError(msg)
            if not self.columns or len(self.columns) < 2:
                msg = (
                    f"check '{self.check.value}' requires 'columns' "
                    f"with >= 2 entries"
                )
                raise ValueError(msg)
        else:
            if self.columns is not None:
                msg = (
                    f"check '{self.check.value}' uses 'column', "
                    f"not 'columns'"
                )
                raise ValueError(msg)
            if self.column is None:
                msg = f"check '{self.check.value}' requires 'column'"
                raise ValueError(msg)

        # value presence
        if self.check in _NO_VALUE_CHECKS and self.value is not None:
            msg = f"check '{self.check.value}' must not have a value"
            raise ValueError(msg)
        if (
            self.check not in _NO_VALUE_CHECKS
            and not is_col_cmp
            and self.value is None
        ):
            msg = f"check '{self.check.value}' requires a value"
            raise ValueError(msg)

        # other_column
        if is_col_cmp and self.other_column is None:
            msg = f"check '{self.check.value}' requires 'other_column'"
            raise ValueError(msg)
        if not is_col_cmp and self.other_column is not None:
            msg = (
                f"check '{self.check.value}' must not have 'other_column'"
            )
            raise ValueError(msg)

        # each_item
        if self.each_item and self.check not in _EACH_ITEM_CHECKS:
            msg = (
                f"'each_item' is not valid for check "
                f"'{self.check.value}'"
            )
            raise ValueError(msg)

        return self


class DatasetSpec(BaseModel):
    """Specification for validating a single dataset."""

    name: str
    source_model: str | None = None
    id_column: str = "id"
    rules: list[Rule]


class ValidationSpec(BaseModel):
    """Root IR document: a versioned collection of dataset validation specs."""

    version: str = "1"
    datasets: list[DatasetSpec]
