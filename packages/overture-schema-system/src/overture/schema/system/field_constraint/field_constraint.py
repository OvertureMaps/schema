"""
Interface for constraints that apply to a single Pydantic field.

- If you are authoring new field-level constraints, this module is for you: you will very likely
  want to derive a subclass of `FieldConstraint` (or of a more specific base class such as
  `CollectionConstraint`).
- If you are looking to reuse existing constraints, this module is too low-level for you. You need
  one of the peer modules that implements a specific constraint type.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, ValidationInfo
from pydantic_core import core_schema


def _normalized(value: object) -> object:
    """Reduce a constraint attribute to a hashable, value-stable form.

    A compiled `re.Pattern` carries identity equality -- two patterns built
    from the same source compare unequal -- so it reduces to `(pattern, flags)`.
    Containers reduce to sorted tuples so equal contents hash equal regardless
    of insertion order. The sort by repr is stable because `FieldConstraint`
    requires attribute values to be value types (see its docstring), so every
    leaf reduces to a value-stable form.
    """
    if isinstance(value, re.Pattern):
        return (value.pattern, value.flags)
    if isinstance(value, Mapping):
        return tuple(sorted(((k, _normalized(v)) for k, v in value.items()), key=repr))
    if isinstance(value, (list, tuple)):
        return tuple(_normalized(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_normalized(v) for v in value), key=repr))
    return value


class FieldConstraint(ABC):
    """Base class for field-level constraints.

    Constraints are value objects: two instances of the same concrete type
    carrying the same attributes are equal and hash equal, so a set of
    constraints deduplicates by rule. Equality keys on the concrete type, so a
    fixed-pattern subclass never equals a raw `PatternConstraint` with the same
    pattern.

    Subclass attributes participate in equality and hashing, so they must be
    value types -- scalars, `re.Pattern`, or containers of these. An attribute
    that compares by object identity leaves equality ill-defined.
    """

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FieldConstraint) or type(self) is not type(other):
            return NotImplemented
        return self._identity() == other._identity()

    def __hash__(self) -> int:
        return hash((type(self), self._identity()))

    def _identity(self) -> tuple[tuple[str, object], ...]:
        return tuple(
            (name, _normalized(value)) for name, value in sorted(vars(self).items())
        )

    def validate(self, value: Any, info: ValidationInfo) -> None:  # noqa: B027
        """Validate the value and raise `ValidationError` if invalid."""
        pass

    @abstractmethod
    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Generate Pydantic core schema."""
        pass

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        """
        Generate JSON schema.

        Override in subclasses for custom schema.
        """
        return handler(core_schema)
