"""Constraint-based validation for Overture Maps schemas."""

import re
from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import Any, get_origin

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema


class BaseConstraint(ABC):
    """Base class for all constraints."""

    def validate(self, value: Any, info: ValidationInfo) -> None:  # noqa: B027
        """Validate the value and raise ValidationError if invalid."""
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
        """Generate JSON schema. Override in subclasses for custom schema."""
        return handler(core_schema)


class StringConstraint(BaseConstraint):
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


class CollectionConstraint(BaseConstraint):
    """Base class for collection-based constraints."""

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Let the handler generate the proper schema for the collection type
        python_schema = handler(source)

        def validate_collection(value: Any, info: ValidationInfo) -> Any:
            self.validate(value, info)
            return value

        return core_schema.with_info_after_validator_function(
            validate_collection, python_schema
        )

    @staticmethod
    def _is_collection_type(source: type[Any]) -> bool:
        origin = get_origin(source)
        if origin is not None:
            return issubclass(origin, Collection)
        else:
            return issubclass(source, Collection)


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
    """IETF BCP-47 language tag constraint."""

    def __init__(self, allow_private_use: bool = True):
        self.allow_private_use = allow_private_use
        # More permissive BCP-47 validation to handle various valid formats
        self.pattern = re.compile(
            r"^[a-z]{2,3}(-[A-Za-z]{2,8})*(-[0-9][A-Za-z0-9]{3})*$"
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


class ISO8601DateTimeConstraint(StringConstraint):
    """ISO 8601 datetime constraint."""

    def __init__(self) -> None:
        # Simplified ISO 8601 validation
        self.pattern = re.compile(
            r"^([1-9]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T"
            r"([01]\d|2[0-3]):([0-5]\d):([0-5]\d|60)(\.\d{1,3})?"
            r"(Z|[-+]([01]\d|2[0-3]):[0-5]\d)$"
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
                        ctx={"error": f"Invalid ISO 8601 datetime: {value}"},
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["format"] = "date-time"
        json_schema["description"] = "ISO 8601 datetime"
        return json_schema


class JSONPointerConstraint(StringConstraint):
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


class MinItemsConstraint(CollectionConstraint):
    """Minimum items constraint for collections."""

    def __init__(self, min_items: int):
        if not isinstance(min_items, int):
            raise ValueError(
                f"min_items must be an int, got {type(min_items).__name__}"
            )
        if min_items < 1:
            raise ValueError(f"min_items must be positive, got {min_items}")
        self.min_items = min_items

    def validate(self, value: Any, info: ValidationInfo) -> None:
        num_items = len(value)
        if num_items < self.min_items:
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
                            "error": f"Collection has too few items: expected len>={self.min_items} but got len={num_items}"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        schema_type = json_schema.get("type")
        if schema_type == "array":
            json_schema["minItems"] = self.min_items
        elif schema_type == "object":
            json_schema["minProperties"] = self.min_items
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


class UniqueItemsConstraint(CollectionConstraint):
    """Constraint to ensure all items in a collection are unique."""

    def validate(self, value: list[Any], info: ValidationInfo) -> None:
        if len(value) != len(set(value)):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={"error": "All items must be unique"},
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["uniqueItems"] = True
        return json_schema


class ConfidenceScoreConstraint(BaseConstraint):
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


class ZoomLevelConstraint(BaseConstraint):
    """Constraint for map zoom levels (0 to 23)."""

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Use built-in constraints for validation
        return core_schema.int_schema(ge=0, le=23)

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["minimum"] = 0
        json_schema["maximum"] = 23
        json_schema["description"] = "Map zoom level between 0 and 23"
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


class CompositeUniqueConstraint(CollectionConstraint):
    """Constraint for composite uniqueness validation using attribute extraction."""

    def __init__(self, *attribute_paths: str):
        """Initialize with attribute paths to extract for uniqueness comparison.

        Args:
            *attribute_paths: Attribute names or paths to extract from each item
                             for uniqueness comparison (e.g., 'value', 'type')
        """
        if not attribute_paths:
            raise ValueError("At least one attribute path must be specified")
        self.attribute_paths = attribute_paths

    def validate(self, value: list[Any], info: ValidationInfo) -> None:
        """Validate that items are unique based on composite attribute values."""
        composite_keys = []

        for item in value:
            # Extract attribute values to create composite key
            key_parts = []
            for attr_path in self.attribute_paths:
                if hasattr(item, attr_path):
                    key_parts.append(getattr(item, attr_path))
                elif isinstance(item, dict) and attr_path in item:
                    key_parts.append(item[attr_path])
                else:
                    # If attribute doesn't exist, use None as part of key
                    key_parts.append(None)

            composite_keys.append(tuple(key_parts))

        # Check for duplicates
        if len(composite_keys) != len(set(composite_keys)):
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)

            # Find the duplicated keys for better error message
            seen = set()
            duplicates = set()
            for key in composite_keys:
                if key in seen:
                    duplicates.add(key)
                seen.add(key)

            attr_names = ", ".join(self.attribute_paths)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"Items must be unique based on ({attr_names}). Found duplicates: {list(duplicates)}"
                        },
                    )
                ],
            )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["uniqueItems"] = True
        attr_names = ", ".join(self.attribute_paths)
        json_schema["description"] = f"Items must be unique based on ({attr_names})"
        return json_schema


class PatternPropertiesDictConstraint(BaseConstraint):
    """Constraint for dictionaries with pattern-validated keys that require additionalProperties: false.

    This constraint ensures that dictionaries using patternProperties in their JSON Schema
    have additionalProperties set to false, preventing keys that don't match the declared
    pattern from being accepted.

    Use this when you have a dict[SomeConstrainedType, ValueType] where SomeConstrainedType
    uses a pattern constraint and you want to enforce that only keys matching that pattern
    are allowed.
    """

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return handler(source)

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        # Ensure additionalProperties is false for pattern-based dictionaries
        if "patternProperties" in json_schema:
            json_schema["additionalProperties"] = False
        return json_schema


class ExtensionPrefixModelConstraint(BaseConstraint):
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
