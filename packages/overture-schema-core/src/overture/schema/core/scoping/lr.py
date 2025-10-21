from typing import Annotated, Any, NewType

from pydantic import Field, GetJsonSchemaHandler, ValidationError, ValidationInfo
from pydantic_core import InitErrorDetails, core_schema

from overture.schema.system.field_constraint import CollectionConstraint
from overture.schema.system.primitive import float64

GeometricPosition = Annotated[float, Field(ge=0, le=1)]
GeometricRange = Annotated[list[GeometricPosition], Field(min_length=2, max_length=2)]
# One possible advantage to using percentages over absolute distances is being able to
# trivially validate that the position lies "on" its segment (i.e. is between zero and
# one). Of course, this level of validity doesn't mean the number isn't nonsense
LinearlyReferencedPosition = NewType(
    "LinearlyReferencedPosition",
    Annotated[
        float64,
        Field(
            description="Represents a linearly-referenced position between 0% and 100% of the distance along a path such as a road segment or a river center-line segment.",
            ge=0.0,
            le=1.0,
        ),
    ],
)


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
        self, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(schema)
        json_schema["type"] = "array"
        json_schema["minItems"] = 2
        json_schema["maxItems"] = 2
        json_schema["items"] = {"type": "number", "minimum": 0.0, "maximum": 1.0}
        json_schema["description"] = (
            "Linear reference range [start, end] where 0.0 <= start < end <= 1.0"
        )
        return json_schema


LinearlyReferencedRange = NewType(
    "LinearlyReferencedRange",
    Annotated[
        list[LinearlyReferencedPosition],
        LinearReferenceRangeConstraint(),
        Field(
            description="Represents a non-empty range of positions along a path as a pair linearly-referenced positions. For example, the pair [0.25, 0.5] represents the range beginning 25% of the distance from the start of the path and ending 50% of the distance from the path",
        ),
    ],
)
