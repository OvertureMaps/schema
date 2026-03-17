"""Parametrized tests for resolve_types function."""

from typing import get_args
from unittest.mock import Mock, patch

import pytest
from overture.schema.cli.commands import resolve_types
from overture.schema.system.discovery import ModelKey

DISCOVER_MODELS = "overture.schema.cli.commands.discover_models"


# Mock model classes
class Place:
    pass


class Segment:
    pass


class Connector:
    pass


class Building:
    pass


class Sources:
    pass


# Mock ModelKey instances
BUILDING_KEY = ModelKey(
    name="building",
    entry_point="mock:MyClass",
    tags=frozenset({"feature", "overture", "overture:theme=buildings"}),
)
SEGMENT_KEY = ModelKey(
    name="segment",
    entry_point="mock:Segment",
    tags=frozenset({"feature", "overture", "overture:theme=transportation"}),
)
CONNECTOR_KEY = ModelKey(
    name="connector",
    entry_point="mock:Connector",
    tags=frozenset({"feature", "overture", "overture:theme=transportation"}),
)
PLACE_KEY = ModelKey(
    name="place",
    entry_point="mock:Place",
    tags=frozenset({"feature", "overture", "overture:theme=places"}),
)
SOURCES_KEY = ModelKey(
    name="sources",
    entry_point="mock:Sources",
    tags=frozenset({"overture"}),
)

MOCK_MODELS = {
    BUILDING_KEY: Building,
    SEGMENT_KEY: Segment,
    CONNECTOR_KEY: Connector,
    PLACE_KEY: Place,
    SOURCES_KEY: Sources,
}


class TestResolveTypes:
    @pytest.mark.parametrize(
        "tags,excluded_tags,type_names,should_succeed",
        [
            pytest.param(
                ("overture:theme=buildings",), (), (), True, id="tag_buildings"
            ),
            pytest.param(
                ("overture:theme=transportation",),
                (),
                (),
                True,
                id="tag_transportation",
            ),
            pytest.param(("overture:theme=places",), (), (), True, id="tag_places"),
            pytest.param(("nonexistent",), (), (), False, id="unknown_tag"),
            pytest.param((), (), ("building",), True, id="type_building"),
            pytest.param((), (), ("segment",), True, id="type_segment"),
            pytest.param((), (), ("nonexistent",), False, id="invalid_type"),
            pytest.param(
                ("overture:theme=buildings",),
                (),
                ("building",),
                True,
                id="tag_and_type_match",
            ),
            pytest.param(
                ("overture:theme=buildings",),
                (),
                ("segment",),
                False,
                id="tag_and_type_mismatch",
            ),
            pytest.param(
                ("overture:theme=transportation",),
                (),
                ("segment", "connector"),
                True,
                id="tag_with_multiple_types",
            ),
            pytest.param((), (), (), True, id="no_filters_all_models"),
        ],
    )
    def test_resolve_types_combinations(
        self,
        tags: tuple[str, ...],
        excluded_tags: tuple[str, ...],
        type_names: tuple[str, ...],
        should_succeed: bool,
    ) -> None:
        with patch(
            DISCOVER_MODELS,
            return_value=MOCK_MODELS,
        ):
            if should_succeed:
                union = resolve_types(tags, excluded_tags, type_names)
                assert union is not None
            else:
                with pytest.raises(ValueError, match="No models found"):
                    resolve_types(tags, excluded_tags, type_names)

    def test_resolve_types_case_sensitive(self) -> None:
        with patch(
            DISCOVER_MODELS,
            return_value=MOCK_MODELS,
        ):
            # Lowercase should work
            union = resolve_types((), (), ("building",))
            assert union is not None
            # Uppercase should fail
            with pytest.raises(ValueError, match="No models found"):
                resolve_types((), (), ("BUILDING",))

    def test_resolve_types_empty_result_error_message(self) -> None:
        with patch(
            DISCOVER_MODELS,
            return_value=MOCK_MODELS,
        ):
            with pytest.raises(ValueError) as exc_info:
                resolve_types(("nonexistent",), (), ("also_fake",))
            assert "No models found" in str(exc_info.value)

    def test_resolve_types_excluded_tags(self) -> None:
        with patch(
            DISCOVER_MODELS,
            return_value=MOCK_MODELS,
        ):
            # Exclude 'overture:theme=buildings' tag
            union = resolve_types((), ("overture:theme=buildings",), ())
            # Should not include Building model
            assert not any(issubclass(model, Mock) for model in get_args(union))

    def test_resolve_types_no_filters_returns_all(self) -> None:
        with patch(
            DISCOVER_MODELS,
            return_value=MOCK_MODELS,
        ):
            union = resolve_types((), (), ())
            # Should include all mock models
            assert all(
                any(issubclass(model, t) for model in getattr(union, "__args__", []))
                for t in [Building, Segment, Connector, Place, Sources]
            )
