import re
from typing import Any

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
    """Generic pattern-based string constraint."""

    def __init__(self, pattern: str, error_message: str, flags: int = 0):
        self.pattern = re.compile(pattern, flags)
        self.pattern_str = pattern
        self.error_message = error_message

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={"error": self.error_message.format(value=value)},
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern_str
        return json_schema


########################################################################
# String constraints for specific use cases (organized alphabetically) #
########################################################################


class CountryCodeAlpha2Constraint(StringConstraint):
    """Allows only ISO 3166-1 alpha-2 country codes."""

    def __init__(self) -> None:
        self.pattern = re.compile(r"^[A-Z]{2}$")

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"Invalid ISO 3166-1 alpha-2 country code: {value}"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["minLength"] = 2
        json_schema["maxLength"] = 2
        json_schema["description"] = "ISO 3166-1 alpha-2 country code"
        return json_schema


class HexColorConstraint(StringConstraint):
    """Allows only hexadecimal color codes (e.g., #FF0000 or #FFF)."""

    def __init__(self) -> None:
        self.pattern = re.compile(r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"Invalid hexadecimal color format: {value}. Must be in format #RGB or #RRGGBB (e.g., #FFF or #FF0000)"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["description"] = "Hexadecimal color code in format #RGB or #RRGGBB"
        return json_schema


class JsonPointerConstraint(StringConstraint):
    """Allows only valid JSON Pointer values (RFC 6901)."""

    def validate(self, value: str, info: ValidationInfo) -> None:
        # Empty string represents root pointer
        if value == "":
            return

        if not value.startswith("/"):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"JSON Pointer must start with '/' or be empty string: {value}"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["description"] = "JSON Pointer (RFC 6901)"
        return json_schema


class LanguageTagConstraint(StringConstraint):
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
        # In understanding the regular expression, remark that '(:?' indicates a non-capturing
        # group, and that all the top-level or non-nested groups represent top-level components of
        # `langtag` referenced in the syntax section of https://www.rfc-editor.org/rfc/bcp/bcp47.txt.
        # In particular, the top-level groups in left-to-right order represent:
        #
        # 1. language
        # 2. ["-" script]
        # 3. ["-" region]
        # 4. *("-" variant)
        # 5. *("-" extension)
        self.pattern = re.compile(
            r"^(?:(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}?)|(?:[A-Za-z]{4,8}))(?:-[A-Za-z]{4})?(?:-[A-Za-z]{2}|[0-9]{3})?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(?:-[A-WY-Za-wy-z0-9](?:-[A-Za-z0-9]{2,8})+)*$"
        )

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={"error": f"Invalid IETF BCP-47 language tag: {value}"},
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["description"] = "IETF BCP-47 language tag"
        return json_schema


class NoWhitespaceConstraint(StringConstraint):
    """Allows only strings that contain no whitespace characters."""

    def __init__(self) -> None:
        self.pattern = re.compile(r"^\S+$")

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"String cannot contain whitespace characters: '{value}'"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["description"] = "String without whitespace characters"
        return json_schema


class SnakeCaseConstraint(StringConstraint):
    """Allows only strings that look like snake case identifiers, *e.g.* `"foo_bar"`."""

    def __init__(self) -> None:
        self.pattern = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"Invalid category format: {value}. Must be snake_case (lowercase letters, numbers, underscores)"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["description"] = "Category in snake_case format"
        return json_schema


class StrippedConstraint(StringConstraint):
    """Allows only strings that have no leading/trailing whitespace."""

    def validate(self, value: str, info: ValidationInfo) -> None:
        if value != value.strip():
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"String cannot have leading or trailing whitespace: {repr(value)}"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = r"^(\S.*)?\S$"
        json_schema["description"] = "String with no leading/trailing whitespace"
        return json_schema


class PhoneNumberConstraint(StringConstraint):
    """Constraint for international phone numbers."""

    def __init__(self) -> None:
        self.pattern = re.compile(r"^\+\d{1,3}[\s\-\(\)0-9]+$")

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"Invalid phone number format: {value}. Must start with + and country code"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["description"] = (
            "International phone number (+ followed by country code and number)"
        )
        return json_schema


class RegionCodeConstraint(StringConstraint):
    """ISO 3166-2 principal subdivision code constraint."""

    def __init__(self) -> None:
        self.pattern = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,3}$")

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={"error": f"Invalid ISO 3166-2 subdivision code: {value}"},
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["minLength"] = 4
        json_schema["maxLength"] = 6
        json_schema["description"] = "ISO 3166-2 subdivision code"
        return json_schema


class WikidataIdConstraint(StringConstraint):
    """Constraint for Wikidata identifiers (Q followed by digits)."""

    def __init__(self) -> None:
        self.pattern = re.compile(r"^Q\d+$")

    def validate(self, value: str, info: ValidationInfo) -> None:
        if not self.pattern.match(value):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"Invalid Wikidata identifier: {value}. Must be Q followed by digits (e.g., Q123)"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern.pattern
        json_schema["description"] = "Wikidata identifier (Q followed by digits)"
        return json_schema
