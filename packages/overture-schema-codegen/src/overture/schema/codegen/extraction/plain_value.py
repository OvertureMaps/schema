"""The plain value of a schema value, for code that turns values into text."""

from enum import Enum

__all__ = ["plain_value"]


def plain_value(value: object) -> object:
    """Return *value*, or its `.value` when it is an `Enum` member.

    Any schema value may arrive here: a condition value, a `Literal`
    argument or an example value is a string, number or `None` as often as
    an enum member, so the parameter is `object` and non-members pass
    through unchanged.

    A member must not be formatted directly. From Python 3.11, `format()`
    and f-strings of a mixed-in member such as `class Kind(str, Enum)`, a
    `DocumentedEnum` included, give `Kind.ROAD` rather than `road`, and
    `repr()` gives the member on every version.
    """
    return value.value if isinstance(value, Enum) else value
