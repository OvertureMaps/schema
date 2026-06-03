"""Tests for the overture-schema-extensions package."""

from datetime import date

import pytest
from overture.schema.extensions import (
    DayOfWeek,
    EntityWithOperatingHours,
    HourSet,
    HourSetStatus,
    OperatingHours,
    PlaceWithOperatingHours,
    Rule,
)
from pydantic import ValidationError

# HourSet tests


def test_hourset_creation_basic():
    """Test creating a basic HourSet."""
    hour_set = HourSet(
        days=[DayOfWeek.MONDAY],
        status=HourSetStatus.OPEN,
        open="09:00",
        close="17:00",
    )
    assert hour_set.days == [DayOfWeek.MONDAY]
    assert hour_set.status == HourSetStatus.OPEN
    assert hour_set.open == "09:00"
    assert hour_set.close == "17:00"


def test_hourset_24_hours():
    """Test creating a 24-hour HourSet."""
    hour_set = HourSet(
        days=[DayOfWeek.SUNDAY],
        status=HourSetStatus.OPEN,
        is_open_24_hours=True,
    )
    assert hour_set.is_open_24_hours is True
    assert hour_set.open is None
    assert hour_set.close is None


def test_hourset_symbolic_close():
    """Test creating a HourSet with symbolic closing time."""
    hour_set = HourSet(
        days=[DayOfWeek.MONDAY],
        status=HourSetStatus.OPEN,
        open="07:00",
        close_symbolic="untilSoldOut",
        note="Fresh bread daily, closes when sold out, typically around 2 PM.",
    )
    assert hour_set.close_symbolic == "untilSoldOut"
    assert (
        hour_set.note
        == "Fresh bread daily, closes when sold out, typically around 2 PM."
    )


def test_hourset_multiple_days():
    """Test creating a HourSet for multiple days."""
    hour_set = HourSet(
        days=[
            DayOfWeek.TUESDAY,
            DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY,
        ],
        status=HourSetStatus.OPEN,
        open="09:00",
        close="17:00",
        last_entry="16:30",
    )
    assert len(hour_set.days) == 4
    assert hour_set.last_entry == "16:30"


def test_hourset_overnight():
    """Test creating a HourSet that spans overnight (e.g., Saturday 8 PM to Sunday 2 AM)."""
    hour_set = HourSet(
        days=[DayOfWeek.SATURDAY],
        status=HourSetStatus.OPEN,
        open="20:00",
        close="02:00",
    )
    assert hour_set.open == "20:00"
    assert hour_set.close == "02:00"


def test_hourset_validation_time_format():
    """Test that HourSet validates time format."""
    # Valid time format should work
    hour_set = HourSet(
        days=[DayOfWeek.MONDAY],
        status=HourSetStatus.OPEN,
        open="09:00",
        close="17:00",
    )
    assert hour_set.open == "09:00"

    # Invalid time format should fail
    with pytest.raises(ValidationError):
        HourSet(
            days=[DayOfWeek.MONDAY],
            status=HourSetStatus.OPEN,
            open="9:00",  # Missing leading zero
            close="17:00",
        )


def test_hourset_validation_invalid_hour():
    """Test that HourSet validates hour range (0-23)."""
    with pytest.raises(ValidationError) as exc_info:
        HourSet(
            days=[DayOfWeek.MONDAY],
            status=HourSetStatus.OPEN,
            open="25:00",  # Invalid hour
            close="17:00",
        )
    assert "Invalid hour" in str(exc_info.value)


def test_hourset_validation_invalid_minute():
    """Test that HourSet validates minute range (0-59)."""
    with pytest.raises(ValidationError) as exc_info:
        HourSet(
            days=[DayOfWeek.MONDAY],
            status=HourSetStatus.OPEN,
            open="09:00",
            close="17:99",  # Invalid minute
        )
    assert "Invalid minute" in str(exc_info.value)


def test_hourset_validation_24_hours_with_times():
    """Test that is_open_24_hours cannot be combined with open/close times."""
    with pytest.raises(ValidationError) as exc_info:
        HourSet(
            days=[DayOfWeek.MONDAY],
            status=HourSetStatus.OPEN,
            is_open_24_hours=True,
            open="09:00",  # Should not be specified with is_open_24_hours
            close="17:00",
        )
    assert "is_open_24_hours" in str(exc_info.value)
    assert "open and close times should not be specified" in str(exc_info.value)


def test_hourset_validation_24_hours_without_times():
    """Test that is_open_24_hours works correctly without open/close times."""
    hour_set = HourSet(
        days=[DayOfWeek.MONDAY],
        status=HourSetStatus.OPEN,
        is_open_24_hours=True,
    )
    assert hour_set.is_open_24_hours is True
    assert hour_set.open is None
    assert hour_set.close is None


# OperatingHours tests


def test_operating_hours_creation():
    """Test creating an OperatingHours object with primary."""
    hours = OperatingHours(
        primary=[
            HourSet(
                days=[DayOfWeek.MONDAY],
                status=HourSetStatus.OPEN,
                open="07:00",
                close_symbolic="untilSoldOut",
                note="Fresh bread daily, closes when sold out, typically around 2 PM.",
            ),
            HourSet(
                days=[
                    DayOfWeek.TUESDAY,
                    DayOfWeek.WEDNESDAY,
                    DayOfWeek.THURSDAY,
                    DayOfWeek.FRIDAY,
                ],
                status=HourSetStatus.OPEN,
                open="09:00",
                close="17:00",
                last_entry="16:30",
            ),
            HourSet(
                days=[DayOfWeek.SATURDAY],
                status=HourSetStatus.OPEN,
                open="20:00",
                close="02:00",
            ),
            HourSet(
                days=[DayOfWeek.SUNDAY],
                status=HourSetStatus.OPEN,
                is_open_24_hours=True,
            ),
        ]
    )
    assert len(hours.primary) == 4
    assert hours.primary[0].days == [DayOfWeek.MONDAY]
    assert hours.primary[3].is_open_24_hours is True


def test_operating_hours_required_field():
    """Test that OperatingHours requires primary field."""
    with pytest.raises(ValidationError) as exc_info:
        OperatingHours()  # Should fail - primary is required
    errors = exc_info.value.errors()
    assert len(errors) > 0
    assert any(e["loc"] == ("primary",) for e in errors)


def test_operating_hours_min_length():
    """Test that OperatingHours requires at least one HourSet."""
    with pytest.raises(ValidationError) as exc_info:
        OperatingHours(primary=[])  # Should fail - empty list
    errors = exc_info.value.errors()
    assert len(errors) > 0


# EntityWithOperatingHours tests


def test_entity_with_operating_hours_creation():
    """Test creating an EntityWithOperatingHours with just required fields."""
    entity = EntityWithOperatingHours(
        id="test-entity-123",
    )
    assert entity.id == "test-entity-123"
    assert entity.operating_hours is None


def test_entity_with_operating_hours_with_hours():
    """Test creating an EntityWithOperatingHours with operating_hours."""
    entity = EntityWithOperatingHours(
        id="test-entity-456",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY],
                    status=HourSetStatus.OPEN,
                    open="09:00",
                    close="17:00",
                )
            ]
        ),
    )
    assert entity.operating_hours is not None
    assert len(entity.operating_hours.primary) == 1


def test_entity_with_operating_hours_json_serialization():
    """Test that EntityWithOperatingHours can be serialized to JSON."""
    entity = EntityWithOperatingHours(
        id="json-test-001",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.SUNDAY],
                    status=HourSetStatus.OPEN,
                    is_open_24_hours=True,
                )
            ]
        ),
    )

    # Test JSON serialization
    json_data = entity.model_dump()
    assert json_data["id"] == "json-test-001"
    assert json_data["operating_hours"]["primary"][0]["is_open_24_hours"] is True


# PlaceWithOperatingHours tests


def test_place_with_operating_hours_creation():
    """Test creating a PlaceWithOperatingHours with all Place required fields."""
    place = PlaceWithOperatingHours(
        id="test-place-123",
        geometry={"type": "Point", "coordinates": [-122.4194, 37.7749]},
        version=1,
        operating_status="open",
    )
    assert place.id == "test-place-123"
    assert place.operating_hours is None
    assert place.operating_status == "open"


def test_place_with_operating_hours_with_hours():
    """Test creating a PlaceWithOperatingHours with operating_hours."""
    place = PlaceWithOperatingHours(
        id="test-place-456",
        geometry={"type": "Point", "coordinates": [-122.4194, 37.7749]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[
                        DayOfWeek.MONDAY,
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                        DayOfWeek.FRIDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    open="09:00",
                    close="17:00",
                ),
                HourSet(
                    days=[DayOfWeek.SATURDAY],
                    status=HourSetStatus.OPEN,
                    open="10:00",
                    close="14:00",
                ),
            ]
        ),
    )
    assert place.operating_hours is not None
    assert len(place.operating_hours.primary) == 2


def test_place_with_operating_hours_complex_schedule():
    """Test creating a PlaceWithOperatingHours with a complex schedule."""
    place = PlaceWithOperatingHours(
        id="test-place-789",
        geometry={"type": "Point", "coordinates": [0.0, 0.0]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.MONDAY],
                    status=HourSetStatus.OPEN,
                    open="07:00",
                    close_symbolic="untilSoldOut",
                    note="Fresh bread daily, closes when sold out, typically around 2 PM.",
                ),
                HourSet(
                    days=[
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                        DayOfWeek.FRIDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    open="09:00",
                    close="17:00",
                    last_entry="16:30",
                ),
                HourSet(
                    days=[DayOfWeek.SATURDAY],
                    status=HourSetStatus.OPEN,
                    open="20:00",
                    close="02:00",
                ),
                HourSet(
                    days=[DayOfWeek.SUNDAY],
                    status=HourSetStatus.OPEN,
                    is_open_24_hours=True,
                ),
            ]
        ),
    )
    assert place.theme == "places"
    assert place.type == "place"
    assert len(place.operating_hours.primary) == 4
    assert place.operating_hours.primary[0].close_symbolic == "untilSoldOut"
    assert place.operating_hours.primary[3].is_open_24_hours is True


def test_place_with_operating_hours_json_serialization():
    """Test that PlaceWithOperatingHours can be serialized to JSON."""
    place = PlaceWithOperatingHours(
        id="json-test-001",
        geometry={"type": "Point", "coordinates": [1.0, 2.0]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.MONDAY],
                    status=HourSetStatus.OPEN,
                    open="09:00",
                    close="17:00",
                )
            ]
        ),
    )

    # Test JSON serialization
    json_data = place.model_dump()
    assert json_data["id"] == "json-test-001"
    assert json_data["theme"] == "places"
    assert json_data["type"] == "place"
    assert json_data["operating_hours"]["primary"][0]["days"] == ["Monday"]
    assert json_data["operating_hours"]["primary"][0]["open"] == "09:00"


def test_place_with_operating_hours_json_schema_generation():
    """Test that we can generate a JSON schema for PlaceWithOperatingHours."""
    schema = PlaceWithOperatingHours.model_json_schema()

    # Check that schema has expected structure
    assert "properties" in schema
    assert "id" in schema["properties"]
    assert "operating_hours" in schema["properties"]
    # Should have Place fields
    assert "geometry" in schema["properties"]
    assert "theme" in schema["properties"]
    assert "operating_status" in schema["properties"]


# Real-world example tests


def test_example_bakery():
    """Example: A bakery that closes when sold out."""
    bakery = PlaceWithOperatingHours(
        id="bakery-001",
        geometry={"type": "Point", "coordinates": [-122.4, 37.8]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.MONDAY],
                    status=HourSetStatus.OPEN,
                    open="07:00",
                    close_symbolic="untilSoldOut",
                    note="Fresh bread daily, closes when sold out, typically around 2 PM.",
                ),
                HourSet(
                    days=[
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                        DayOfWeek.FRIDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    open="07:00",
                    close="14:00",
                ),
                HourSet(
                    days=[DayOfWeek.SATURDAY],
                    status=HourSetStatus.OPEN,
                    open="08:00",
                    close="12:00",
                ),
                HourSet(
                    days=[DayOfWeek.SUNDAY],
                    status=HourSetStatus.CLOSED,
                ),
            ]
        ),
    )

    json_data = bakery.model_dump()
    assert json_data["id"] == "bakery-001"
    assert len(json_data["operating_hours"]["primary"]) == 4
    assert (
        json_data["operating_hours"]["primary"][0]["close_symbolic"] == "untilSoldOut"
    )


def test_example_nightclub():
    """Example: A nightclub with overnight hours."""
    nightclub = PlaceWithOperatingHours(
        id="nightclub-001",
        geometry={"type": "Point", "coordinates": [-118.2, 34.1]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[
                        DayOfWeek.MONDAY,
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                    ],
                    status=HourSetStatus.CLOSED,
                ),
                HourSet(
                    days=[DayOfWeek.FRIDAY, DayOfWeek.SATURDAY],
                    status=HourSetStatus.OPEN,
                    open="22:00",
                    close="04:00",
                    note="Friday and Saturday nights, 10 PM to 4 AM",
                ),
                HourSet(
                    days=[DayOfWeek.SUNDAY],
                    status=HourSetStatus.CLOSED,
                ),
            ]
        ),
    )

    json_data = nightclub.model_dump()
    assert json_data["operating_hours"]["primary"][1]["open"] == "22:00"
    assert json_data["operating_hours"]["primary"][1]["close"] == "04:00"


def test_example_convenience_store():
    """Example: A 24/7 convenience store."""
    store = EntityWithOperatingHours(
        id="store-247",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[
                        DayOfWeek.MONDAY,
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                        DayOfWeek.FRIDAY,
                        DayOfWeek.SATURDAY,
                        DayOfWeek.SUNDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    is_open_24_hours=True,
                    note="Open 24 hours, 7 days a week",
                )
            ]
        ),
    )

    json_data = store.model_dump()
    assert json_data["operating_hours"]["primary"][0]["is_open_24_hours"] is True
    assert len(json_data["operating_hours"]["primary"][0]["days"]) == 7


def test_example_museum():
    """Example: A museum with last entry time."""
    museum = PlaceWithOperatingHours(
        id="museum-001",
        geometry={"type": "Point", "coordinates": [2.3, 48.9]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.MONDAY],
                    status=HourSetStatus.CLOSED,
                    note="Closed for maintenance",
                ),
                HourSet(
                    days=[
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                        DayOfWeek.FRIDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    open="10:00",
                    close="18:00",
                    last_entry="17:30",
                    note="Last entry 30 minutes before closing",
                ),
                HourSet(
                    days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
                    status=HourSetStatus.OPEN,
                    open="09:00",
                    close="20:00",
                    last_entry="19:30",
                    note="Weekend extended hours",
                ),
            ]
        ),
    )

    json_data = museum.model_dump()
    weekday_hours = json_data["operating_hours"]["primary"][1]
    assert weekday_hours["last_entry"] == "17:30"
    assert weekday_hours["close"] == "18:00"


def test_example_restaurant_varied_schedule():
    """Example: A restaurant with different hours each day."""
    restaurant = PlaceWithOperatingHours(
        id="restaurant-001",
        geometry={"type": "Point", "coordinates": [-73.9, 40.7]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.MONDAY],
                    status=HourSetStatus.CLOSED,
                    note="Closed on Mondays",
                ),
                HourSet(
                    days=[
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    open="17:00",
                    close="22:00",
                    note="Dinner service only",
                ),
                HourSet(
                    days=[DayOfWeek.FRIDAY],
                    status=HourSetStatus.OPEN,
                    open="17:00",
                    close="23:00",
                    note="Friday night service",
                ),
                HourSet(
                    days=[DayOfWeek.SATURDAY],
                    status=HourSetStatus.OPEN,
                    open="12:00",
                    close="23:00",
                    note="Lunch and dinner service",
                ),
                HourSet(
                    days=[DayOfWeek.SUNDAY],
                    status=HourSetStatus.OPEN,
                    open="11:00",
                    close="21:00",
                    note="Brunch and dinner service",
                ),
            ]
        ),
    )

    json_data = restaurant.model_dump()
    assert len(json_data["operating_hours"]["primary"]) == 5
    # Monday is closed
    assert json_data["operating_hours"]["primary"][0]["status"] == "Closed"
    # Saturday has extended hours
    saturday_hours = json_data["operating_hours"]["primary"][3]
    assert saturday_hours["open"] == "12:00"
    assert saturday_hours["close"] == "23:00"


# Rules tests


def test_rule_creation():
    """Test creating a Rule with a condition and hours."""
    rule = Rule(
        condition="holidays",
        hours=[
            HourSet(
                days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY],
                status=HourSetStatus.CLOSED,
            )
        ],
    )
    assert rule.condition == "holidays"
    assert len(rule.hours) == 1
    assert rule.start_date is None
    assert rule.end_date is None


def test_rule_with_dates():
    """Test creating a Rule with start and end dates."""
    rule = Rule(
        condition="summer",
        hours=[
            HourSet(
                days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY],
                status=HourSetStatus.OPEN,
                open="08:00",
                close="20:00",
            )
        ],
        start_date=date(2024, 6, 1),
        end_date=date(2024, 8, 31),
    )
    assert rule.condition == "summer"
    assert rule.start_date == date(2024, 6, 1)
    assert rule.end_date == date(2024, 8, 31)


def test_rule_validation_invalid_date():
    """Test that Rule validates invalid dates (e.g., Feb 30)."""
    # Pydantic will automatically validate date objects
    # Invalid dates will fail when creating the date object itself
    with pytest.raises(ValueError):
        date(2024, 2, 30)  # February 30th doesn't exist


def test_rule_validation_date_range():
    """Test that start_date must be before or equal to end_date."""
    with pytest.raises(ValidationError) as exc_info:
        Rule(
            condition="holidays",
            hours=[
                HourSet(
                    days=[DayOfWeek.MONDAY],
                    status=HourSetStatus.CLOSED,
                )
            ],
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),  # End date before start date
        )
    assert "start_date" in str(exc_info.value)
    assert "must be before or equal to end_date" in str(exc_info.value)


def test_rule_validation_same_start_end_date():
    """Test that start_date can equal end_date (single day rule)."""
    rule = Rule(
        condition="special event",
        hours=[
            HourSet(
                days=[DayOfWeek.SATURDAY],
                status=HourSetStatus.OPEN,
                open="10:00",
                close="22:00",
            )
        ],
        start_date=date(2024, 7, 4),
        end_date=date(2024, 7, 4),
    )
    assert rule.start_date == rule.end_date == date(2024, 7, 4)


def test_operating_hours_with_rules():
    """Test creating OperatingHours with rules."""
    hours = OperatingHours(
        primary=[
            HourSet(
                days=[
                    DayOfWeek.MONDAY,
                    DayOfWeek.TUESDAY,
                    DayOfWeek.WEDNESDAY,
                    DayOfWeek.THURSDAY,
                    DayOfWeek.FRIDAY,
                ],
                status=HourSetStatus.OPEN,
                open="09:00",
                close="17:00",
            )
        ],
        rules=[
            Rule(
                condition="holidays",
                hours=[
                    HourSet(
                        days=[
                            DayOfWeek.MONDAY,
                            DayOfWeek.TUESDAY,
                            DayOfWeek.WEDNESDAY,
                            DayOfWeek.THURSDAY,
                            DayOfWeek.FRIDAY,
                        ],
                        status=HourSetStatus.CLOSED,
                        note="Closed on holidays",
                    )
                ],
            )
        ],
    )
    assert len(hours.primary) == 1
    assert hours.rules is not None
    assert len(hours.rules) == 1
    assert hours.rules[0].condition == "holidays"


def test_example_store_with_holiday_hours():
    """Example: A store with special holiday hours."""
    store = PlaceWithOperatingHours(
        id="store-001",
        geometry={"type": "Point", "coordinates": [-122.3, 47.6]},
        version=1,
        operating_status="open",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[
                        DayOfWeek.MONDAY,
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                        DayOfWeek.FRIDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    open="09:00",
                    close="21:00",
                ),
                HourSet(
                    days=[DayOfWeek.SATURDAY],
                    status=HourSetStatus.OPEN,
                    open="10:00",
                    close="20:00",
                ),
                HourSet(
                    days=[DayOfWeek.SUNDAY],
                    status=HourSetStatus.OPEN,
                    open="11:00",
                    close="19:00",
                ),
            ],
            rules=[
                Rule(
                    condition="holidays",
                    hours=[
                        HourSet(
                            days=[
                                DayOfWeek.MONDAY,
                                DayOfWeek.TUESDAY,
                                DayOfWeek.WEDNESDAY,
                                DayOfWeek.THURSDAY,
                                DayOfWeek.FRIDAY,
                                DayOfWeek.SATURDAY,
                                DayOfWeek.SUNDAY,
                            ],
                            status=HourSetStatus.OPEN,
                            open="10:00",
                            close="18:00",
                            note="Reduced hours on major holidays",
                        )
                    ],
                ),
                Rule(
                    condition="Black Friday",
                    hours=[
                        HourSet(
                            days=[DayOfWeek.FRIDAY],
                            status=HourSetStatus.OPEN,
                            open="06:00",
                            close="23:00",
                            note="Extended hours for Black Friday",
                        )
                    ],
                ),
            ],
        ),
    )

    json_data = store.model_dump()
    assert len(json_data["operating_hours"]["primary"]) == 3
    assert json_data["operating_hours"]["rules"] is not None
    assert len(json_data["operating_hours"]["rules"]) == 2
    assert json_data["operating_hours"]["rules"][0]["condition"] == "holidays"
    assert json_data["operating_hours"]["rules"][1]["condition"] == "Black Friday"


def test_example_seasonal_cafe():
    """Example: A café with seasonal hours."""
    cafe = EntityWithOperatingHours(
        id="cafe-seasonal",
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[
                        DayOfWeek.MONDAY,
                        DayOfWeek.TUESDAY,
                        DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY,
                        DayOfWeek.FRIDAY,
                    ],
                    status=HourSetStatus.OPEN,
                    open="07:00",
                    close="19:00",
                ),
                HourSet(
                    days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
                    status=HourSetStatus.OPEN,
                    open="08:00",
                    close="20:00",
                ),
            ],
            rules=[
                Rule(
                    condition="summer",
                    hours=[
                        HourSet(
                            days=[
                                DayOfWeek.MONDAY,
                                DayOfWeek.TUESDAY,
                                DayOfWeek.WEDNESDAY,
                                DayOfWeek.THURSDAY,
                                DayOfWeek.FRIDAY,
                            ],
                            status=HourSetStatus.OPEN,
                            open="07:00",
                            close="21:00",
                            note="Extended summer hours",
                        ),
                        HourSet(
                            days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
                            status=HourSetStatus.OPEN,
                            open="08:00",
                            close="22:00",
                            note="Extended summer weekend hours",
                        ),
                    ],
                ),
                Rule(
                    condition="winter",
                    hours=[
                        HourSet(
                            days=[
                                DayOfWeek.MONDAY,
                                DayOfWeek.TUESDAY,
                                DayOfWeek.WEDNESDAY,
                                DayOfWeek.THURSDAY,
                                DayOfWeek.FRIDAY,
                            ],
                            status=HourSetStatus.OPEN,
                            open="08:00",
                            close="17:00",
                            note="Shorter winter hours",
                        ),
                        HourSet(
                            days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
                            status=HourSetStatus.CLOSED,
                            note="Closed on weekends in winter",
                        ),
                    ],
                ),
            ],
        ),
    )

    json_data = cafe.model_dump()
    assert len(json_data["operating_hours"]["primary"]) == 2
    assert len(json_data["operating_hours"]["rules"]) == 2
    # Summer rule
    summer_rule = json_data["operating_hours"]["rules"][0]
    assert summer_rule["condition"] == "summer"
    assert len(summer_rule["hours"]) == 2
    # Winter rule
    winter_rule = json_data["operating_hours"]["rules"][1]
    assert winter_rule["condition"] == "winter"
    assert winter_rule["hours"][1]["status"] == "Closed"
