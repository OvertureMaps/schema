"""Tests for the operating-hours extension package."""

from datetime import date
from typing import cast

import pytest
from overture.schema.extensions.operating_hours import (
    DayOfWeek,
    HourSet,
    HourSetStatus,
    OperatingHours,
    Rule,
)
from overture.schema.places import Place
from overture.schema.system.discovery import (
    TagSelector,
    discover_models,
    select_models,
)
from overture.schema.system.extension import create_extended_model, wrap_extension
from overture.schema.system.geometric import Geometry
from pydantic import BaseModel, ValidationError

# The extended Place model, built through the real extension mechanism (wrap + merge).
_maybe_wrapper = wrap_extension("operating_hours", OperatingHours)
assert _maybe_wrapper is not None
_WRAPPER: type[BaseModel] = _maybe_wrapper
PlaceWithOperatingHours: type[BaseModel] = create_extended_model(
    Place, {"operating_hours": _WRAPPER}
)


def _point() -> Geometry:
    return Geometry.from_wkt("POINT (-122.4194 37.7749)")


def _model(value: object) -> type[BaseModel]:
    assert isinstance(value, type) and issubclass(value, BaseModel)
    return value


def _field(model: BaseModel, name: str) -> object:
    return cast(object, getattr(model, name))


# ---------------------------------------------------------------------------
# HourSet model behaviour
# ---------------------------------------------------------------------------


def test_hourset_creation_basic() -> None:
    hour_set = HourSet(
        days=[DayOfWeek.MONDAY],
        status=HourSetStatus.OPEN,
        open="09:00",
        close="17:00",
    )
    assert hour_set.days == [DayOfWeek.MONDAY]
    assert hour_set.open == "09:00"


def test_hourset_24_hours() -> None:
    hour_set = HourSet(
        days=[DayOfWeek.SUNDAY],
        status=HourSetStatus.OPEN,
        is_open_24_hours=True,
    )
    assert hour_set.is_open_24_hours is True
    assert hour_set.open is None


def test_hourset_invalid_time_format() -> None:
    with pytest.raises(ValidationError):
        HourSet(
            days=[DayOfWeek.MONDAY],
            status=HourSetStatus.OPEN,
            open="9:00",  # missing leading zero
        )


def test_hourset_invalid_hour() -> None:
    with pytest.raises(ValidationError):
        HourSet(
            days=[DayOfWeek.MONDAY],
            status=HourSetStatus.OPEN,
            open="25:00",
        )


def test_hourset_24_hours_with_times_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        HourSet(
            days=[DayOfWeek.MONDAY],
            status=HourSetStatus.OPEN,
            is_open_24_hours=True,
            open="09:00",
            close="17:00",
        )
    assert "open and close times should not be specified" in str(exc_info.value)


# ---------------------------------------------------------------------------
# OperatingHours / Rule model behaviour
# ---------------------------------------------------------------------------


def test_operating_hours_requires_primary() -> None:
    with pytest.raises(ValidationError):
        OperatingHours()  # type: ignore[call-arg]  # missing `primary` is the point


def test_operating_hours_min_length() -> None:
    with pytest.raises(ValidationError):
        OperatingHours(primary=[])


def test_rule_date_range_validation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Rule(
            condition="holidays",
            hours=[HourSet(days=[DayOfWeek.MONDAY], status=HourSetStatus.CLOSED)],
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),
        )
    assert "must be before or equal to end_date" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Extended Place model
# ---------------------------------------------------------------------------


def test_extended_place_has_field() -> None:
    assert "operating_hours" in PlaceWithOperatingHours.model_fields
    assert issubclass(PlaceWithOperatingHours, Place)


def test_extended_place_default_none() -> None:
    place = PlaceWithOperatingHours(
        id="test-place-123",
        theme="places",
        type="place",
        version=1,
        geometry=_point(),
        operating_status="open",
    )
    assert _field(place, "operating_hours") is None
    assert _field(place, "operating_status") == "open"


def test_extended_place_with_hours() -> None:
    place = PlaceWithOperatingHours(
        id="test-place-456",
        theme="places",
        type="place",
        version=1,
        geometry=_point(),
        operating_hours=OperatingHours(
            primary=[
                HourSet(
                    days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY],
                    status=HourSetStatus.OPEN,
                    open="09:00",
                    close="17:00",
                ),
            ]
        ),
    )
    operating_hours = _field(place, "operating_hours")
    assert isinstance(operating_hours, OperatingHours)
    assert len(operating_hours.primary) == 1


def test_extended_place_json_serialization() -> None:
    place = PlaceWithOperatingHours(
        id="json-test-001",
        theme="places",
        type="place",
        version=1,
        geometry=_point(),
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
    # Feature serialises to GeoJSON, nesting non-geometry fields under "properties".
    data = place.model_dump(mode="json")
    assert data["properties"]["operating_hours"]["primary"][0]["open"] == "09:00"
    # Round-trips back to an equivalent model via the GeoJSON JSON form.
    restored = PlaceWithOperatingHours.model_validate_json(place.model_dump_json())
    assert _field(restored, "operating_hours") is not None


def test_plain_place_rejects_operating_hours() -> None:
    # The bare Place model does not know the extension field; per the OvertureFeature `ext_*`
    # rule, an unknown top-level property is rejected.
    with pytest.raises(ValidationError):
        Place(  # type: ignore[call-arg]  # `operating_hours` is an unknown field — the point
            id="x",
            theme="places",
            type="place",
            version=1,
            geometry=_point(),
            operating_hours={"primary": []},
        )


# ---------------------------------------------------------------------------
# Discovery integration (relies on installed entry points)
# ---------------------------------------------------------------------------


def test_discovery_tags_extension() -> None:
    models = discover_models()
    by_name = {key.name: key for key in models}
    assert "operating_hours" in by_name
    assert "extension" in by_name["operating_hours"].tags


def test_discovery_applies_extension_to_place() -> None:
    models = discover_models()
    place = next(m for k, m in models.items() if k.name == "place")
    assert "operating_hours" in _model(place).model_fields


def test_discovery_without_apply_extensions_leaves_place_bare() -> None:
    models = discover_models(apply_extensions=False)
    place = next(m for k, m in models.items() if k.name == "place")
    assert "operating_hours" not in _model(place).model_fields


def test_select_models_by_extension_tag() -> None:
    models = discover_models()
    # Engaging the "extension" tag lifts the default hiding query-wide.
    extensions = select_models(models, TagSelector(include_any=("extension",)))
    names = {key.name for key in extensions}
    assert "operating_hours" in names
