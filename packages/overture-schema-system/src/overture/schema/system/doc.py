"""
Documentation support.

This module enables documenting things that "native Python" doesn't have a documentation solution
for.
"""

from enum import Enum
from typing import TypeVar, cast

T = TypeVar("T", bound="DocumentedEnum")


class DocumentedEnum(Enum):
    """
    Base class for enumerations whose members have their own documentation strings.

    For historical reasons, the Python enumeration system does not recognize docstrings on
    enumeration members. This limitation is usually not a problem, since in many use cases,
    enumeration members are self-documenting, or they can be documented with Python comments, or
    they can be documented at the level of the enumeration class.

    However, when authoring schemas in Pydantic, the inability to document enumeration members
    in a Python-native manner becomes problematic. Sometimes enumerations may have many members,
    the members may have subtleties that aren't obvious from the name, and it is desirable for
    code generation tools to have access to metadata that they can use to document the code
    generated for the enumeration members.

    Supporting this use case is the narrow purpose of this class. It should not be used to document
    builder-facing enumerations whose primary audience is builders who are authoring schemas or
    extending the schema system itself. Builder-facing enumerations can be documented with comments
    or with pseudo-docstrings that the `pdoc` tool will understand and bring into the API reference,
    even if Python doesn't understand them.

    Examples
    --------
    A documented enumeration:

    >>> class Status(str, DocumentedEnum):
    ...     PENDING = ("pending", "Request is awaiting review")
    ...     APPROVED = ("approved", "Request has been approved")
    ...     REJECTED = ("rejected", "Request has been rejected")
    >>> Status.PENDING.__doc__
    'Request is awaiting review'

    Documentation is optional on a per-member basis:

    >>> class ConnectionState(str, DocumentedEnum):
    ...     CONNECTED = "connected"
    ...     DISCONNECTED = "disconnected"
    ...     QUIESCING = (
    ...         "quiescing",
    ...         "Gracefully shutting down, rejecting new requests but completing existing ones",
    ...     )
    >>> ConnectionState.CONNECTED.__doc__ is None
    True
    >>> ConnectionState.QUIESCING.__doc__
    'Gracefully shutting down, rejecting new requests but completing existing ones'

    The previous examples showed the common case of multiple inheritance from `str`, but this is
    not necessary. The enum can be another type such as `int`:

    >>> class Priority(int, DocumentedEnum):
    ...     LOW = 1
    ...     MEDIUM = 5
    ...     HIGH = (10, "High priority should only be used by system processes.")

    Or it can be of no particular type:

    >>> class HttpStatus(DocumentedEnum):
    ...     OK = (200, "The request succeeded")
    ...     NOT_FOUND = (404, "The server cannot find the requested resource")
    ...     INTERNAL_SERVER_ERROR = (500, "The server encountered an unexpected condition")
    """

    def __new__(cls: type, value: object, doc: str | None = None) -> "DocumentedEnum":
        if len(cls.__bases__) == 2:
            base_cls = next(base for base in cls.__bases__ if base != Enum)
            obj = cast(DocumentedEnum, base_cls.__new__(cls, value))
        elif len(cls.__bases__) > 2:
            raise TypeError(
                f"too many base classes: only 1-2 are supported, but `{cls.__name__}` has {len(cls.__bases__)}: {repr(cls.__bases__)}"
            )
        else:
            obj = cast(DocumentedEnum, object.__new__(cls))
        obj._value_ = value
        obj.__doc__ = doc
        return cast(DocumentedEnum, obj)
