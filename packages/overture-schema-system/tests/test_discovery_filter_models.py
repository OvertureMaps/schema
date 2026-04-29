"""Direct coverage of filter_models combinator algebra."""

from pydantic import BaseModel

from overture.schema.system.discovery import (
    ModelDict,
    ModelKey,
    TagSelector,
    filter_models,
)


# Mock model classes
class Building(BaseModel):
    pass


class Segment(BaseModel):
    pass


class Connector(BaseModel):
    pass


class Place(BaseModel):
    pass


class Sources(BaseModel):
    pass


BUILDING_KEY = ModelKey(
    name="building",
    entry_point="mock:Building",
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
    tags=frozenset({"feature", "overture", "overture:theme=places", "draft"}),
)
SOURCES_KEY = ModelKey(
    name="sources",
    entry_point="mock:Sources",
    tags=frozenset({"overture"}),
)

ALL_MODELS: ModelDict = {
    BUILDING_KEY: Building,
    SEGMENT_KEY: Segment,
    CONNECTOR_KEY: Connector,
    PLACE_KEY: Place,
    SOURCES_KEY: Sources,
}


def names(models: ModelDict) -> set[str]:
    """Return the set of model names in a ModelDict."""
    return {key.name for key in models}


class TestEmptySelector:
    def test_empty_selector_returns_all(self) -> None:
        result = filter_models(ALL_MODELS)
        assert names(result) == names(ALL_MODELS)

    def test_empty_selector_explicit(self) -> None:
        result = filter_models(ALL_MODELS, TagSelector())
        assert names(result) == names(ALL_MODELS)


class TestIncludeAny:
    def test_single_tag(self) -> None:
        result = filter_models(
            ALL_MODELS, TagSelector(include_any=("overture:theme=buildings",))
        )
        assert names(result) == {"building"}

    def test_multi_tag_or(self) -> None:
        result = filter_models(
            ALL_MODELS,
            TagSelector(
                include_any=(
                    "overture:theme=buildings",
                    "overture:theme=transportation",
                )
            ),
        )
        assert names(result) == {"building", "segment", "connector"}

    def test_no_match(self) -> None:
        result = filter_models(
            ALL_MODELS, TagSelector(include_any=("overture:theme=nonexistent",))
        )
        assert result == {}

    def test_mixed_match(self) -> None:
        result = filter_models(
            ALL_MODELS,
            TagSelector(
                include_any=("overture:theme=buildings", "overture:theme=nonexistent")
            ),
        )
        assert names(result) == {"building"}


class TestRequireAll:
    def test_single_tag(self) -> None:
        result = filter_models(ALL_MODELS, TagSelector(require_all=("feature",)))
        assert names(result) == {"building", "segment", "connector", "place"}

    def test_multi_tag_and_match(self) -> None:
        result = filter_models(
            ALL_MODELS, TagSelector(require_all=("feature", "overture"))
        )
        assert names(result) == {"building", "segment", "connector", "place"}

    def test_multi_tag_and_one_fails(self) -> None:
        result = filter_models(
            ALL_MODELS, TagSelector(require_all=("feature", "draft"))
        )
        assert names(result) == {"place"}

    def test_no_match(self) -> None:
        result = filter_models(
            ALL_MODELS, TagSelector(require_all=("feature", "nonexistent"))
        )
        assert result == {}


class TestExcludeAny:
    def test_single_tag(self) -> None:
        result = filter_models(
            ALL_MODELS, TagSelector(exclude_any=("overture:theme=buildings",))
        )
        assert "building" not in names(result)
        assert names(result) == {"segment", "connector", "place", "sources"}

    def test_multi_tag_or(self) -> None:
        result = filter_models(
            ALL_MODELS,
            TagSelector(
                exclude_any=(
                    "overture:theme=buildings",
                    "overture:theme=transportation",
                )
            ),
        )
        assert names(result) == {"place", "sources"}

    def test_no_match_keeps_all(self) -> None:
        result = filter_models(ALL_MODELS, TagSelector(exclude_any=("nonexistent",)))
        assert names(result) == names(ALL_MODELS)


class TestTypeNames:
    def test_single(self) -> None:
        result = filter_models(ALL_MODELS, type_names=("building",))
        assert names(result) == {"building"}

    def test_multiple(self) -> None:
        result = filter_models(ALL_MODELS, type_names=("building", "place"))
        assert names(result) == {"building", "place"}

    def test_none_match(self) -> None:
        result = filter_models(ALL_MODELS, type_names=("nonexistent",))
        assert result == {}


class TestCrossCombinator:
    def test_include_then_require(self) -> None:
        # Scope to features (places, transportation), narrow to those
        # also tagged "draft" → only place qualifies.
        result = filter_models(
            ALL_MODELS,
            TagSelector(
                include_any=(
                    "overture:theme=places",
                    "overture:theme=transportation",
                ),
                require_all=("draft",),
            ),
        )
        assert names(result) == {"place"}

    def test_include_then_exclude(self) -> None:
        # Scope to all themed features, exclude buildings.
        result = filter_models(
            ALL_MODELS,
            TagSelector(
                include_any=(
                    "overture:theme=buildings",
                    "overture:theme=transportation",
                    "overture:theme=places",
                ),
                exclude_any=("overture:theme=buildings",),
            ),
        )
        assert names(result) == {"segment", "connector", "place"}

    def test_all_three_combinators_plus_type_names(self) -> None:
        # Scope to features in either places or transportation,
        # require feature tag, exclude drafts, restrict to segment by name.
        result = filter_models(
            ALL_MODELS,
            TagSelector(
                include_any=(
                    "overture:theme=places",
                    "overture:theme=transportation",
                ),
                require_all=("feature",),
                exclude_any=("draft",),
            ),
            type_names=("segment",),
        )
        assert names(result) == {"segment"}


class TestIdempotence:
    def test_double_application(self) -> None:
        selector = TagSelector(
            include_any=("overture:theme=buildings", "overture:theme=places")
        )
        once = filter_models(ALL_MODELS, selector)
        twice = filter_models(once, selector)
        assert names(once) == names(twice)


class TestInputInvariance:
    def test_returns_new_dict(self) -> None:
        result = filter_models(ALL_MODELS)
        assert result is not ALL_MODELS
