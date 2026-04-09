"""
Constraints on fields with string values.
"""

import re
from typing import Any, NoReturn

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema

from .field_constraint import FieldConstraint

###################################
# General string constraint types #
###################################


class StringConstraint(FieldConstraint):
    """Base class for string-based constraints."""

    def _raise_validation_error(
        self, value: str, info: ValidationInfo, message: str
    ) -> NoReturn:
        context = info.context or {}
        loc = context.get("loc_prefix", ()) + ("value",)
        raise ValidationError.from_exception_data(
            title=self.__class__.__name__,
            line_errors=[
                InitErrorDetails(
                    type="value_error",
                    loc=loc,
                    input=value,
                    ctx={"error": message},
                )
            ],
        )

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        python_schema = handler(str)

        def validate_string(value: str, info: ValidationInfo) -> str:
            self.validate(value, info)
            return value

        return core_schema.with_info_after_validator_function(
            validate_string, python_schema
        )


class PatternConstraint(StringConstraint):
    """Generic pattern-based string constraint.

    Parameters
    ----------
    pattern : str
        Regular expression to match against.
    error_message : str
        Error message template. Use `{value}` to interpolate the failing
        value (the only available placeholder).
    flags : int
        Regex flags passed to `re.compile`.
    description : str or None
        JSON Schema `description` annotation.
    min_length : int or None
        JSON Schema `minLength` annotation.
    max_length : int or None
        JSON Schema `maxLength` annotation.
    """

    def __init__(
        self,
        pattern: str,
        error_message: str,
        flags: int = 0,
        *,
        description: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
    ):
        self.pattern = re.compile(pattern, flags)
        self.error_message = error_message
        self.description = description
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            self._raise_validation_error(
                value, info, self.error_message.format(value=value)
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        if self.description is not None:
            json_schema["description"] = self.description
        if self.min_length is not None:
            json_schema["minLength"] = self.min_length
        if self.max_length is not None:
            json_schema["maxLength"] = self.max_length
        return json_schema


########################################################################
# String constraints for specific use cases (organized alphabetically) #
########################################################################


class CountryCodeAlpha2Constraint(PatternConstraint):
    """Allows only ISO 3166-1 alpha-2 country codes."""

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^[A-Z]{2}$",
            error_message="Invalid ISO 3166-1 alpha-2 country code: {value}",
            description="ISO 3166-1 alpha-2 country code",
            min_length=2,
            max_length=2,
        )


class HexColorConstraint(PatternConstraint):
    """Allows only hexadecimal color codes (e.g., #FF0000 or #FFF)."""

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$",
            error_message="Invalid hexadecimal color format: {value}. Must be in format #RGB or #RRGGBB (e.g., #FFF or #FF0000)",
            description="Hexadecimal color code in format #RGB or #RRGGBB",
        )


class JsonPointerConstraint(StringConstraint):
    """Allows only valid JSON Pointer values (RFC 6901)."""

    def validate(self, value: str, info: ValidationInfo) -> None:
        # Empty string represents root pointer
        if value == "":
            return

        if not value.startswith("/"):
            self._raise_validation_error(
                value,
                info,
                f"JSON Pointer must start with '/' or be empty string: {value}",
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["description"] = "JSON Pointer (RFC 6901)"
        return json_schema


class LanguageTagConstraint(PatternConstraint):
    """
    Allows only `BCP-47`_ language tags.

    This constraint validates BCP-47 language tags at the lexical or syntactic level. It verifies
    that candidate tags follow the grammar described in the RFC, but **not** that they are validly
    registered in IANA's `language subtag registry`_. In other words, this constraint can tell you
    that it *looks like* a real language tag, but not that it *is* a real language tag.

    .. _BCP-47: https://www.rfc-editor.org/rfc/bcp/bcp47.txt
    .. _language subtag registry: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
    """

    def __init__(self) -> None:
        # Top-level groups in the pattern (left-to-right) correspond to BCP-47 langtag components:
        # 1. language, 2. ["-" script], 3. ["-" region], 4. *("-" variant), 5. *("-" extension)
        # See: https://www.rfc-editor.org/rfc/bcp/bcp47.txt
        super().__init__(
            pattern=r"^(?:(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}?)|(?:[A-Za-z]{4,8}))(?:-[A-Za-z]{4})?(?:-[A-Za-z]{2}|[0-9]{3})?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(?:-[A-WY-Za-wy-z0-9](?:-[A-Za-z0-9]{2,8})+)*$",
            error_message="Invalid IETF BCP-47 language tag: {value}",
            description="IETF BCP-47 language tag",
        )


class NoWhitespaceConstraint(PatternConstraint):
    """Allows only strings that contain no whitespace characters."""

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^\S+$",
            error_message="String cannot contain whitespace characters: '{value}'",
            description="String without whitespace characters",
        )


class SnakeCaseConstraint(PatternConstraint):
    """Allows only strings that look like snake case identifiers, *e.g.* `"foo_bar"`."""

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^[a-z0-9]+(_[a-z0-9]+)*$",
            error_message="Invalid category format: {value}. Must be snake_case (lowercase letters, numbers, underscores)",
            description="Category in snake_case format",
        )


class StrippedConstraint(PatternConstraint):
    r"""Allows only strings that have no leading/trailing whitespace.

    Uses ``\Z`` (absolute end-of-string) instead of ``$`` because
    Python's ``$`` matches before a trailing ``\n``. ECMA regex (used by
    JSON Schema) treats ``$`` as absolute end-of-string, so the JSON
    schema output swaps ``\Z`` back to ``$``.
    """

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^(\S(.*\S)?)?\Z",
            error_message="String cannot have leading or trailing whitespace: {value}",
            description="String with no leading/trailing whitespace",
        )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = super().__get_pydantic_json_schema__(core_schema, handler)
        json_schema["pattern"] = self.pattern.pattern.replace(r"\Z", "$")
        return json_schema


class PhoneNumberConstraint(PatternConstraint):
    """Allows only international phone numbers."""

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^\+\d{1,3}[\s\-\(\)0-9]+$",
            error_message="Invalid phone number format: {value}. Must start with + and country code",
            description="International phone number (+ followed by country code and number)",
        )


class RegionCodeConstraint(PatternConstraint):
    """Allows only ISO 3166-2 principal subdivision codes."""

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$",
            error_message="Invalid ISO 3166-2 subdivision code: {value}",
            description="ISO 3166-2 subdivision code",
            min_length=4,
            max_length=6,
        )


class WikidataIdConstraint(PatternConstraint):
    """Allows only Wikidata identifiers (Q followed by digits)."""

    def __init__(self) -> None:
        super().__init__(
            pattern=r"^Q\d+$",
            error_message="Invalid Wikidata identifier: {value}. Must be Q followed by digits (e.g., Q123)",
            description="Wikidata identifier (Q followed by digits)",
        )
