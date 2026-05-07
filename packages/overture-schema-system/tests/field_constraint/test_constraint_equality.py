"""Value-equality semantics for `FieldConstraint` subclasses.

Two constraints of the same concrete type with the same attributes are equal
and hash equal, so a set of constraints deduplicates by rule rather than by
object identity. Equality keys on the concrete type, so a subclass with a fixed
pattern never equals a raw `PatternConstraint` carrying the same pattern.
"""

import re
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from overture.schema.system.field_constraint import (
    CountryCodeAlpha2Constraint,
    FieldConstraint,
    HexColorConstraint,
    JsonPointerConstraint,
    PatternConstraint,
    UniqueItemsConstraint,
)


class TestMarkerConstraintEquality:
    def test_equal_instances_compare_and_hash_equal(self) -> None:
        a, b = UniqueItemsConstraint(), UniqueItemsConstraint()
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_distinct_marker_classes_unequal(self) -> None:
        assert UniqueItemsConstraint() != JsonPointerConstraint()


class TestParametricConstraintEquality:
    def test_fixed_pattern_subclass_instances_equal(self) -> None:
        a, b = CountryCodeAlpha2Constraint(), CountryCodeAlpha2Constraint()
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_distinct_pattern_subclasses_unequal(self) -> None:
        assert CountryCodeAlpha2Constraint() != HexColorConstraint()

    def test_equal_raw_patterns_collapse(self) -> None:
        a = PatternConstraint(r"^[a-z]+$", "err")
        b = PatternConstraint(r"^[a-z]+$", "err")
        assert a == b
        assert hash(a) == hash(b)

    def test_pattern_flags_distinguish(self) -> None:
        a = PatternConstraint(r"^[a-z]+$", "err")
        b = PatternConstraint(r"^[a-z]+$", "err", re.IGNORECASE)
        assert a != b

    def test_subclass_not_equal_to_base_with_same_state(self) -> None:
        """A fixed-pattern subclass is a distinct rule from a raw equivalent."""
        country = CountryCodeAlpha2Constraint()
        raw = PatternConstraint(
            country.pattern.pattern,
            country.error_message,
            description=country.description,
            min_length=country.min_length,
            max_length=country.max_length,
        )
        assert country != raw


class _ListConstraint(FieldConstraint):
    """Test-only constraint with a list-valued attribute."""

    def __init__(self, items: list[str]) -> None:
        self.items = list(items)

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return handler(source)


class _DictConstraint(FieldConstraint):
    """Test-only constraint with a dict-valued attribute."""

    def __init__(self, mapping: dict[str, int]) -> None:
        self.mapping = dict(mapping)

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return handler(source)


class TestContainerValuedAttributes:
    """A future constraint with a container attribute stays a hashable value."""

    def test_equal_list_attr_instances_collapse(self) -> None:
        a, b = _ListConstraint(["a", "b"]), _ListConstraint(["a", "b"])
        assert a == b
        assert len({a, b}) == 1

    def test_distinct_list_attr_instances_unequal(self) -> None:
        assert _ListConstraint(["a", "b"]) != _ListConstraint(["a", "c"])

    def test_equal_dict_attr_instances_collapse(self) -> None:
        a = _DictConstraint({"x": 1, "y": 2})
        b = _DictConstraint({"y": 2, "x": 1})
        assert a == b
        assert len({a, b}) == 1
