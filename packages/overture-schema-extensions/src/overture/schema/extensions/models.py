"""
Extended Overture Place models with operating hours.
"""

from datetime import date
from enum import Enum
from typing import Annotated

from overture.schema.places import Place
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.ref import Identified
from pydantic import BaseModel, Field, field_validator, model_validator


class HourSetStatus(str, Enum):
    """Status of an entity during specified hours."""

    OPEN = "Open"
    CLOSED = "Closed"


class DayOfWeek(str, Enum):
    """Days of the week."""

    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


@no_extra_fields
class HourSet(BaseModel):
    """
    A set of operating hours for specific days of the week.

    Represents operating hours for one or more days, with flexible options for
    standard hours, 24-hour operation, or symbolic closing times.
    """

    # Required

    days: Annotated[
        list[DayOfWeek],
        Field(
            min_length=1,
            description="Days of the week these hours apply to",
        ),
        UniqueItemsConstraint(),
    ]

    status: Annotated[
        HourSetStatus,
        Field(description="Whether the entity is open or closed during these hours"),
    ]

    # Optional - Time fields

    open: Annotated[
        str | None,
        Field(
            description='Opening time in 24-hour format (e.g., "09:00")',
            pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        ),
    ] = None

    close: Annotated[
        str | None,
        Field(
            description='Closing time in 24-hour format (e.g., "17:00")',
            pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        ),
    ] = None

    close_symbolic: Annotated[
        str | None,
        Field(
            description='Symbolic closing time (e.g., "untilSoldOut", "untilDusk")',
        ),
    ] = None

    last_entry: Annotated[
        str | None,
        Field(
            description='Last entry time in 24-hour format (e.g., "16:30")',
            pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        ),
    ] = None

    # Optional - Special cases

    is_open_24_hours: Annotated[
        bool | None,
        Field(description="Whether the entity is open 24 hours on these days"),
    ] = None

    note: Annotated[
        str | None,
        Field(description="Additional notes about these hours"),
    ] = None

    @field_validator("open", "close", "last_entry")
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        """Validate that time values are valid HH:MM format with correct ranges."""
        if v is not None:
            try:
                hours, minutes = map(int, v.split(":"))
                if hours > 23:
                    raise ValueError(f"Invalid hour: {hours}. Must be 0-23.")
                if minutes > 59:
                    raise ValueError(f"Invalid minute: {minutes}. Must be 0-59.")
            except (ValueError, AttributeError) as e:
                if "Invalid" in str(e):
                    raise
                raise ValueError(f"Invalid time format: {v}. Expected HH:MM format.")
        return v

    @model_validator(mode="after")
    def check_24_hour_consistency(self) -> "HourSet":
        """Ensure 24-hour operation doesn't have conflicting time specifications."""
        if self.is_open_24_hours and (self.open or self.close):
            raise ValueError(
                "When is_open_24_hours is True, open and close times should not be specified"
            )
        return self


@no_extra_fields
class Rule(BaseModel):
    """
    A conditional rule that modifies operating hours under specific conditions.

    Rules allow for exception-based scheduling, such as holiday hours, seasonal
    variations, or special event hours. Optional date fields can specify when
    the rule is valid.
    """

    # Required

    condition: Annotated[
        str,
        Field(
            description='Condition when this rule applies (e.g., "holidays", "summer", "during festivals")',
        ),
    ]

    hours: Annotated[
        list[HourSet],
        Field(
            min_length=1,
            description="Operating hours when this condition is true",
        ),
    ]

    # Optional

    start_date: Annotated[
        date | None,
        Field(
            description="Start date when this rule becomes active (ISO 8601 format: YYYY-MM-DD)",
        ),
    ] = None

    end_date: Annotated[
        date | None,
        Field(
            description="End date when this rule expires (ISO 8601 format: YYYY-MM-DD)",
        ),
    ] = None

    @model_validator(mode="after")
    def check_date_range(self) -> "Rule":
        """Ensure start_date is before or equal to end_date if both are specified."""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError(
                    f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})"
                )
        return self


@no_extra_fields
class OperatingHours(BaseModel):
    """
    Operating hours specification for a place.

    Contains primary hours with detailed day-by-day schedules, and optional
    conditional rules for exceptions like holidays or seasonal variations.
    """

    # Required

    primary: Annotated[
        list[HourSet],
        Field(
            min_length=1,
            description="Primary operating hours by day of the week",
        ),
    ]

    # Optional

    rules: Annotated[
        list[Rule] | None,
        Field(
            description="Conditional rules that modify hours under specific conditions",
        ),
    ] = None


@no_extra_fields
class EntityWithOperatingHours(Identified):
    """
    A simple entity with just an ID and operating hours.

    This is a lightweight model for datasets that only need to track operating hours by ID,
    without all the Place feature fields like geometry, categories, etc.

    Fields:
    - id: Unique identifier (from Identified mixin)
    - operating_hours: Operating hours information (optional)
    """

    # Optional field

    operating_hours: Annotated[
        OperatingHours | None,
        Field(description="Operating hours information for this entity"),
    ] = None


class PlaceWithOperatingHours(Place):
    """
    An Overture Place with operating hours information.

    This extends the standard Overture Place feature with an additional operating_hours field.

    Inherited fields from Place:
    - id: Unique identifier
    - geometry: Point geometry of the place
    - theme: "places"
    - type: "place"
    - version: Feature version
    - names: Place names
    - categories: Place categories
    - operating_status: Operating status (open, closed, etc.)
    - And all other Place fields...

    Extended field:
    - operating_hours: Structured operating hours information (optional)
    """

    # Extended field

    operating_hours: Annotated[
        OperatingHours | None,
        Field(description="Operating hours information for this place"),
    ] = None
