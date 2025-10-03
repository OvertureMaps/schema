"""Constraint-based validation for Overture Maps schemas."""

from typing import Any

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema

from overture.schema.system.constraint import CollectionConstraint, Constraint


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
