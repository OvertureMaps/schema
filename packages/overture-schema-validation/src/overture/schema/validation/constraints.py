"""Constraint-based validation for Overture Maps schemas."""

import re
from typing import Any

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema

from overture.schema.foundation.constraint import CollectionConstraint, Constraint


class StringConstraint(Constraint):
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


class LanguageTagConstraint(StringConstraint):
    """This pattern recognizes BCP-47 language tags at the lexical or syntactic level.
    It verifies that candidate tags follow the grammar described in the RFC, but not
    that they are validly registered tag in IANA's language subtag registry.

    In understanding the regular expression, remark that '(:?' indicates a non-capturing
    group, and that all the top-level or non-nested groups represent top-level
    components of `langtag` referenced in the syntax section of
    https://www.rfc-editor.org/rfc/bcp/bcp47.txt. In particular, the top-level groups in
    left-to-right order represent:

    1. language
    2. ["-" script]
    3. ["-" region]
    4. *("-" variant)
    5. *("-" extension)
    """

    def __init__(self) -> None:
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


class CountryCodeConstraint(StringConstraint):
    """ISO 3166-1 alpha-2 country code constraint."""

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


class RegionCodeConstraint(StringConstraint):
    """ISO 3166-2 subdivision code constraint."""

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


class JsonPointerConstraint(StringConstraint):
    """JSON Pointer constraint (RFC 6901)."""

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


class LinearReferenceRangeConstraint(CollectionConstraint):
    """Linear reference range constraint (0.0 to 1.0)."""

    def validate(self, value: list[float], info: ValidationInfo) -> None:
        if len(value) != 2:
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
                            "error": f"Linear reference range must have exactly 2 values, got {len(value)}"
                        },
                    )
                ],
            )

        start, end = value
        if not (0.0 <= start <= 1.0 and 0.0 <= end <= 1.0):
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
                            "error": f"Linear reference range values must be between 0.0 and 1.0: [{start}, {end}]"
                        },
                    )
                ],
            )

        if start >= end:
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
                            "error": f"Linear reference range start must be less than end: [{start}, {end}]"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["type"] = "array"
        json_schema["minItems"] = 2
        json_schema["maxItems"] = 2
        json_schema["items"] = {"type": "number", "minimum": 0.0, "maximum": 1.0}
        json_schema["description"] = (
            "Linear reference range [start, end] where 0.0 <= start < end <= 1.0"
        )
        return json_schema


class WhitespaceConstraint(StringConstraint):
    """Constraint to ensure string has no leading/trailing whitespace."""

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


class CategoryPatternConstraint(StringConstraint):
    """Constraint for place category patterns (snake_case)."""

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


class WikidataConstraint(StringConstraint):
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


# TODO: Not understanding why this is needed versus just using vanilla annotation.
class ConfidenceScoreConstraint(Constraint):
    """Constraint for confidence/probability scores (0.0 to 1.0)."""

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Use built-in constraints for validation
        return core_schema.float_schema(ge=0.0, le=1.0)

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["minimum"] = 0.0
        json_schema["maximum"] = 1.0
        json_schema["description"] = "Confidence score between 0.0 and 1.0"
        return json_schema


class HexColorConstraint(StringConstraint):
    """Constraint for hexadecimal color codes (e.g., #FF0000 or #FFF)."""

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


class NoWhitespaceConstraint(StringConstraint):
    """Constraint for strings that cannot contain whitespace characters."""

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


class ExtensionPrefixModelConstraint(Constraint):
    """Constraint for models that allow only ext_* prefixed extra fields.

    This ensures that additional properties beyond those explicitly defined
    must use the ext_ prefix pattern and sets additionalProperties: false
    with patternProperties for the JSON Schema.
    """

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        python_schema = handler(source)

        def validate_extension_prefixes(value: Any, info: ValidationInfo) -> Any:
            """Validate that extra fields use allowed prefixes."""
            if hasattr(value, "__pydantic_extra__") and value.__pydantic_extra__:
                for field_name in value.__pydantic_extra__.keys():
                    if not field_name.startswith("ext_"):
                        context = info.context or {}
                        loc = context.get("loc_prefix", ()) + (field_name,)
                        raise ValidationError.from_exception_data(
                            title=self.__class__.__name__,
                            line_errors=[
                                InitErrorDetails(
                                    type="value_error",
                                    loc=loc,
                                    input=field_name,
                                    ctx={
                                        "error": f"Unrecognized field '{field_name}' must use ext_ prefix"
                                    },
                                )
                            ],
                        )
            return value

        return core_schema.with_info_after_validator_function(
            validate_extension_prefixes, python_schema
        )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)

        # Add patternProperties for ext_* fields and set additionalProperties: false
        json_schema["patternProperties"] = {
            "^ext_.*$": {
                "description": "Additional top-level properties must be prefixed with `ext_`."
            }
        }
        json_schema["additionalProperties"] = False

        return json_schema
