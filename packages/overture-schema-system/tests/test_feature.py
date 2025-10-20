import json
import re
from copy import deepcopy
from typing import Annotated, cast

import pytest
from pydantic import ConfigDict, ValidationError, create_model
from pydantic.json_schema import JsonSchemaValue, JsonValue
from util import assert_subset

from overture.schema.system.feature import Feature, _FieldLevel, _maybe_refactor_schema
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    forbid_if,
    min_fields_set,
    require_any_of,
    require_if,
)
from overture.schema.system.optionality import Omitable
from overture.schema.system.primitive import (
    BBox,
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


class TestSerializeModel:
    @pytest.mark.parametrize(
        "feature,expect",
        [
            (
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
            ),
            (
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
                {
                    "type": "Feature",
                    "id": "foo",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
            ),
            (
                Feature(  # type: ignore[call-arg]
                    bbox=BBox(0, 1, 0, 2), geometry=Geometry.from_wkt("POINT(1 2)")
                ),
                {
                    "type": "Feature",
                    "bbox": [0, 1, 0, 2],
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
            ),
            (
                Feature(
                    id="bar",
                    bbox=BBox(0, 1, 0, 2),
                    geometry=Geometry.from_wkt("POINT(1 2)"),
                ),
                {
                    "type": "Feature",
                    "id": "bar",
                    "bbox": [0, 1, 0, 2],
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
            ),
        ],
    )
    def test_simple_json(self, feature: Feature, expect: dict[str, object]) -> None:
        actual = json.loads(feature.model_dump_json())

        assert expect == actual

    @pytest.mark.parametrize(
        "feature,expect",
        [
            (
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
                {
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
            ),
            (
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
                {
                    "id": "foo",
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
            ),
            (
                Feature(
                    bbox=BBox(0, 1, 0, 2),
                    geometry=Geometry.from_wkt("POINT(1 2)"),  # type: ignore[call-arg]
                ),
                {
                    "bbox": BBox(0, 1, 0, 2),
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
            ),
            (
                Feature(
                    id="bar",
                    bbox=BBox(0, 1, 0, 2),
                    geometry=Geometry.from_wkt("POINT(1 2)"),
                ),
                {
                    "id": "bar",
                    "bbox": BBox(0, 1, 0, 2),
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
            ),
        ],
    )
    def test_simple_python(self, feature: Feature, expect: dict[str, object]) -> None:
        actual = feature.model_dump()

        assert expect == actual

    def test_subclass(self) -> None:
        class SubFeature(Feature):
            foo: int
            bar: Omitable[str]
            baz: bool | None = None

        geometry = Geometry.from_wkt("LINESTRING(0 1, 0 2)")
        sub_feature = SubFeature(id="foo", foo=42, geometry=geometry)  # type: ignore[call-arg]

        actual_json = json.loads(sub_feature.model_dump_json())
        assert {
            "type": "Feature",
            "id": "foo",
            "geometry": {"type": "LineString", "coordinates": [[0, 1], [0, 2]]},
            "properties": {
                "foo": 42,
                "baz": None,
            },
        } == actual_json

        actual_python = sub_feature.model_dump()
        assert {
            "id": "foo",
            "geometry": geometry,
            "foo": 42,
            "baz": None,
        } == actual_python


class TestValidateModel:
    @pytest.mark.parametrize(
        "json_dict,expect",
        [
            (
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
            ),
            (
                {
                    "type": "Feature",
                    "id": "foo",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
            ),
            (
                {
                    "type": "Feature",
                    "bbox": [0, 1, 0, 2],
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
                Feature(  # type: ignore[call-arg]
                    bbox=BBox(0, 1, 0, 2), geometry=Geometry.from_wkt("POINT(1 2)")
                ),
            ),
            (
                {
                    "type": "Feature",
                    "id": "bar",
                    "bbox": [0, 1, 0, 2],
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
                Feature(
                    id="bar",
                    bbox=BBox(0, 1, 0, 2),
                    geometry=Geometry.from_wkt("POINT(1 2)"),
                ),
            ),
        ],
    )
    def test_simple_json(self, json_dict: dict[str, object], expect: Feature) -> None:
        actual = Feature.model_validate_json(json.dumps(json_dict))

        assert expect == actual

    @pytest.mark.parametrize(
        "python_dict,expect",
        [
            (
                {
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
            ),
            (
                {
                    "id": "foo",
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),  # type: ignore[call-arg]
            ),
            (
                {
                    "bbox": BBox(0, 1, 0, 2),
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
                Feature(  # type: ignore[call-arg]
                    bbox=BBox(0, 1, 0, 2), geometry=Geometry.from_wkt("POINT(1 2)")
                ),
            ),
            (
                {
                    "id": "bar",
                    "bbox": BBox(0, 1, 0, 2),
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
                Feature(
                    id="bar",
                    bbox=BBox(0, 1, 0, 2),
                    geometry=Geometry.from_wkt("POINT(1 2)"),
                ),
            ),
        ],
    )
    def test_simple_python(
        self, python_dict: dict[str, object], expect: Feature
    ) -> None:
        actual = Feature.model_validate(python_dict)

        assert expect == actual

    def test_subclass(self) -> None:
        class SubFeature(Feature):
            foo: int
            bar: Omitable[str]
            baz: bool | None = None

        bbox = BBox(0, 1, 0, 2)
        geometry = Geometry.from_wkt("LINESTRING(0 1, 0 2)")
        expect = SubFeature(id="Hello", foo=42, baz=None, bbox=bbox, geometry=geometry)  # type: ignore[call-arg]

        actual_from_json = SubFeature.model_validate_json(
            json.dumps(
                {
                    "type": "Feature",
                    "id": "Hello",
                    "bbox": [0, 1, 0, 2],
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0, 1], [0, 2]],
                    },
                    "properties": {
                        "foo": 42,
                        "baz": None,
                    },
                }
            )
        )
        assert expect == actual_from_json

        actual_from_python = SubFeature.model_validate(
            {
                "id": "Hello",
                "bbox": bbox,
                "geometry": geometry,
                "foo": 42,
                "baz": None,
            }
        )
        assert expect == actual_from_python

    def test_extra_properties(self) -> None:
        class SubFeature(Feature):
            model_config = ConfigDict(extra="allow")

        extra = {
            "foo": "bar",
            "baz": [42],
        }

        input_json = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": extra,
        }

        sub_feature = SubFeature.model_validate_json(json.dumps(input_json))

        assert extra == sub_feature.model_extra

    def test_error_data_not_dict(self) -> None:
        with pytest.raises(
            TypeError, match="feature data must be a `dict`, but 'foo' is a `str`"
        ):
            Feature.model_validate("foo")

        with pytest.raises(
            TypeError, match="feature data must be a `dict`, but 'bar' is a `str`"
        ):
            Feature.model_validate_json('"bar"')

    def test_error_type_property_missing(self) -> None:
        input_json = {
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {},
        }

        with pytest.raises(ValidationError) as error_info:
            Feature.model_validate_json(json.dumps(input_json))

        validation_error = error_info.value
        assert 1 == validation_error.error_count()
        first_error = validation_error.errors()[0]
        assert "missing" == first_error["type"]
        assert "type" == first_error["loc"][0]

    def test_error_type_property_wrong_value(self) -> None:
        input_json = {
            "type": 42,
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": None,
        }

        with pytest.raises(
            ValidationError, match="'type' property has wrong value 42 in feature JSON"
        ) as error_info:
            Feature.model_validate_json(json.dumps(input_json))

        validation_error = error_info.value
        assert 1 == validation_error.error_count()
        first_error = validation_error.errors()[0]
        assert "value_error" == first_error["type"]
        assert "type" == first_error["loc"][0]

    def test_error_properties_missing(self) -> None:
        input_json = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }

        with pytest.raises(ValidationError) as error_info:
            Feature.model_validate_json(json.dumps(input_json))

        validation_error = error_info.value
        assert 1 == validation_error.error_count()
        first_error = validation_error.errors()[0]
        assert "missing" == first_error["type"]
        assert "properties" == first_error["loc"][0]

    def test_error_properties_not_object_or_null(self) -> None:
        input_json = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": 3.14159,
        }

        with pytest.raises(
            ValidationError,
            match="'properties' property has wrong type in feature JSON",
        ) as error_info:
            Feature.model_validate_json(json.dumps(input_json))

        validation_error = error_info.value
        assert 1 == validation_error.error_count()
        first_error = validation_error.errors()[0]
        assert "value_error" == first_error["type"]
        assert "properties" == first_error["loc"][0]

    def test_error_illegal_root_properties(self) -> None:
        input_json = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {},
            "foo": 42,
            "bar": "baz",
        }

        with pytest.raises(
            ValidationError,
            match=r"illegal top-level properties in feature JSON: \['foo', 'bar'\]",
        ) as error_info:
            Feature.model_validate_json(json.dumps(input_json))

        validation_error = error_info.value
        assert 1 == validation_error.error_count()
        first_error = validation_error.errors()[0]
        assert "value_error" == first_error["type"]

    @pytest.mark.parametrize(
        "illegal_properties",
        [
            (("bbox",)),
            (
                (
                    "bbox",
                    "geometry",
                )
            ),
            (
                (
                    "bbox",
                    "geometry",
                    "id",
                )
            ),
            (("geometry",)),
            (
                (
                    "geometry",
                    "id",
                )
            ),
            (("id",)),
        ],
    )
    def test_error_illegal_properties(
        self, illegal_properties: tuple[str, ...]
    ) -> None:
        input_json = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": dict.fromkeys(illegal_properties, "foo"),
        }

        with pytest.raises(
            ValidationError,
            match=f"illegal properties in feature JSON: {re.escape(repr(list(illegal_properties)))}",
        ) as error_info:
            Feature.model_validate_json(json.dumps(input_json))

        validation_error = error_info.value
        assert 1 == validation_error.error_count()
        first_error = validation_error.errors()[0]
        assert "value_error" == first_error["type"]
        assert "properties" == first_error["loc"][0]

    @pytest.mark.parametrize(
        "feature_class,missing_field,json_input,python_input",
        [
            (
                Feature,
                "geometry",
                {"type": "Feature", "properties": None},
                {},
            ),
            (
                Feature,
                "geometry",
                {
                    "type": "Feature",
                    "id": "foo",
                    "bbox": [1, 2, 3, 4],
                    "properties": {},
                },
                {"id": "foo", "bbox": BBox(1, 2, 3, 4)},
            ),
            (
                create_model("SubFeature", __base__=Feature, foo=int),
                "foo",
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [0, 0],
                    },
                    "properties": None,
                },
                {
                    "geometry": Geometry.from_wkt("POINT(0 0)"),
                },
            ),
        ],
    )
    def test_error_required_property_missing(
        self,
        feature_class: type[Feature],
        missing_field: str,
        json_input: dict[str, object],
        python_input: dict[str, object],
    ) -> None:
        def assert_missing(error_info: pytest.ExceptionInfo) -> None:
            validation_error = error_info.value
            assert 1 == validation_error.error_count()
            first_error = validation_error.errors()[0]
            assert "missing" == first_error["type"]
            assert missing_field == first_error["loc"][0]

        with pytest.raises(ValidationError) as json_error_info:
            feature_class.model_validate_json(json.dumps(json_input))

        assert_missing(json_error_info)

        with pytest.raises(ValidationError) as python_error_info:
            feature_class.model_validate(python_input)

        assert_missing(python_error_info)

    @pytest.mark.parametrize(
        "feature_class,invalid_field,json_input,python_input",
        [
            (
                Feature,
                "geometry",
                {"type": "Feature", "geometry": "foo", "properties": {}},
                {"geometry": "foo"},
            ),
            (
                Feature,
                "id",
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "id": 1.5,
                    "properties": None,
                },
                {"geometry": Geometry.from_wkt("POINT(0 0)"), "id": 1.5},
            ),
            (
                Feature,
                "bbox",
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "id": "foo",
                    "bbox": "bar",
                    "properties": None,
                },
                {
                    "geometry": Geometry.from_wkt("POINT(0 0)"),
                    "id": "foo",
                    "bbox": "bar",
                },
            ),
            (
                create_model("SubFeature", __base__=Feature, foo=int),
                "foo",
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": {"foo": "bar"},
                },
                {"geometry": Geometry.from_wkt("POINT(0 0)"), "foo": "bar"},
            ),
        ],
    )
    def test_error_required_property_wrong_value(
        self,
        feature_class: type[Feature],
        invalid_field: str,
        json_input: dict[str, object],
        python_input: dict[str, object],
    ) -> None:
        def assert_wrong_value(
            kind: str, input: dict[str, object], error_info: pytest.ExceptionInfo
        ) -> None:
            validation_error = error_info.value
            first_error = validation_error.errors()[0]

            assert first_error["type"] in {
                "value_error",
                "string_type",
                "int_parsing",
            }, (
                f"unexpected error type {repr(first_error['type'])} for {kind} input {repr(input)}"
            )
            assert invalid_field == first_error["loc"][0], (
                f"unexpected field name {repr(first_error['loc'][0])} for {kind} input {repr(input)}"
            )

        with pytest.raises(ValidationError) as json_error_info:
            feature_class.model_validate_json(json.dumps(json_input))

        assert_wrong_value("json", json_input, json_error_info)

        with pytest.raises(ValidationError) as python_error_info:
            feature_class.model_validate(python_input)

        assert_wrong_value("python", python_input, python_error_info)

    def test_error_extra_property_not_allowed(self) -> None:
        class SubFeature(Feature):
            model_config = ConfigDict(extra="forbid")

        extra = {
            "foo": "bar",
        }

        input_json = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": extra,
        }

        with pytest.raises(ValidationError) as error_info:
            SubFeature.model_validate_json(json.dumps(input_json))

        validation_error = error_info.value
        assert 1 == validation_error.error_count()
        first_error = validation_error.errors()[0]
        assert "extra_forbidden" == first_error["type"]
        assert "foo" == first_error["loc"][0]


class TestJsonSchema:
    def test_simple_json_schema(self) -> None:
        expect = {
            "title": "Feature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {},
                "properties": {
                    "anyOf": [
                        {
                            "type": "object",
                            "not": {"required": ["id", "bbox", "geometry"]},
                        },
                        {
                            "type": "null",
                        },
                    ],
                },
            },
        }

        actual = Feature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_subclass_new_fields(self) -> None:
        class SubFeature(Feature):
            foo: Omitable[int]
            bar: str | None = None
            baz: float

        expect = {
            "title": "SubFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {},
                "properties": {
                    "type": "object",
                    "required": ["baz"],
                    "not": {"required": ["id", "bbox", "geometry"]},
                    "properties": {
                        "foo": {
                            "type": "integer",
                        },
                        "bar": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "null"},
                            ],
                            "default": None,
                        },
                        "baz": {"type": "number"},
                    },
                },
            },
        }

        actual = SubFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_subclass_make_required_fields_not_required(self) -> None:
        """
        A subclass can technically redefine a required field to make it not required. This test
        verifies that the JSON Schema generation works as expected in this scenario.
        """

        class SubFeature(Feature):
            geometry: Omitable[Geometry]  # type: ignore[assignment]

        expect = {
            "title": "SubFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {},
                "properties": {
                    "anyOf": [
                        {
                            "type": "object",
                            "not": {"required": ["id", "bbox", "geometry"]},
                        },
                        {
                            "type": "null",
                        },
                    ],
                },
            },
        }

        actual = SubFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_subclass_geometry_type_constraint(self) -> None:
        class PointFeature(Feature):
            geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.POINT)]

        expect = {
            "title": "PointFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {
                    "type": "object",
                    "required": ["type", "coordinates"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "const": "Point",
                        },
                        "coordinates": {
                            "type": "array",
                            "items": {
                                "type": "number",
                            },
                            "minItems": 2,
                            "maxItems": 3,
                        },
                    },
                },
                "properties": {
                    "anyOf": [
                        {
                            "type": "object",
                            "not": {"required": ["id", "bbox", "geometry"]},
                        },
                        {
                            "type": "null",
                        },
                    ],
                },
            },
        }

        actual = PointFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_forbid_extra_fields_without_adding_fields(self) -> None:
        class SubFeature(Feature):
            model_config = ConfigDict(extra="forbid")

        expect = {
            "title": "SubFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {},
                "properties": {
                    "anyOf": [
                        {
                            "type": "object",
                            "maxProperties": 0,
                        },
                        {
                            "type": "null",
                        },
                    ],
                },
            },
        }

        actual = SubFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_forbid_extra_fields_with_added_optional_field(self) -> None:
        class SubFeature(Feature):
            model_config = ConfigDict(extra="forbid")

            added_field: Omitable[int]

        expect = {
            "title": "SubFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {},
                "properties": {
                    "anyOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "not": {"required": ["id", "bbox", "geometry"]},
                            "properties": {
                                "added_field": {
                                    "type": "integer",
                                },
                            },
                        },
                        {
                            "type": "null",
                        },
                    ],
                },
            },
        }

        actual = SubFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_forbid_extra_fields_with_added_required_field(self) -> None:
        class SubFeature(Feature):
            model_config = ConfigDict(extra="forbid")

            added_field: float

        expect = {
            "title": "SubFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {},
                "properties": {
                    "type": "object",
                    "required": ["added_field"],
                    "not": {"required": ["id", "bbox", "geometry"]},
                    "properties": {
                        "added_field": {
                            "type": "number",
                        },
                    },
                },
            },
        }

        actual = SubFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_unsupported_keyword_min_properties(self) -> None:
        """
        We don't have a clean way to port the JSON Schema "minProperties" keyword to the GeoJSON
        Schema in a way that respects the fact that the "logical" properties of the Feature get
        split, due to the quirks of GeoJSON, between to levels of the Feature object: the top level,
        and the Feature's properties object. Therefore we prohibit this keyword in the Feature
        JSON Schema.
        """

        @min_fields_set(1)
        class MinFieldsFeature(Feature):
            pass

        with pytest.raises(
            ValueError, match="unsupported JSON Schema keyword 'minProperties'"
        ):
            actual = MinFieldsFeature.model_json_schema()
            print(json.dumps(actual, indent=2))

    def test_reuse_synthetic_field_names(self) -> None:
        """
        GeoJSON introduces two artificial field names, "type" and "properties". Since these aren't
        really part of the "logical" structure of a GeoJSON Feature (they are just "physical"
        artifacts of the structure chosen), there is no reason why a model shouldn't be allowed to
        use these field names. This test verifies that every thing works as expected at the JSON
        Schema level when these synthetic field names are used.
        """

        class SyntheticFieldNamesModel(Feature):
            type: int
            properties: str | None = None

        expect: dict[str, object] = {
            "properties": {
                "properties": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {
                            "type": "integer",
                        },
                        "properties": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "null"},
                            ]
                        },
                    },
                }
            }
        }

        actual = SyntheticFieldNamesModel.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, cast(dict[str, object], actual), "expect", "actual")

    def test_model_constraint_top_level_only(self) -> None:
        @forbid_if(["bbox"], FieldEqCondition("id", "hello"))
        @require_if(["id"], FieldEqCondition("bbox", [0, 0, 0, 0]))
        @require_any_of("id", "bbox")
        class TopLevelConstraintFeature(Feature):
            pass

        expect = {
            "title": "TopLevelConstraintFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "anyOf": [
                {"required": ["id"]},
                {"required": ["bbox"]},
            ],
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "bbox": {
                                "const": [0, 0, 0, 0],
                            },
                        },
                    },
                    "then": {
                        "required": ["id"],
                    },
                },
                {
                    "if": {
                        "properties": {
                            "id": {
                                "const": "hello",
                            }
                        }
                    },
                    "then": {
                        "not": {
                            "required": ["bbox"],
                        },
                    },
                },
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {},
                "bbox": {},
                "geometry": {},
                "properties": {
                    "anyOf": [
                        {
                            "type": "object",
                            "not": {"required": ["id", "bbox", "geometry"]},
                        },
                        {"type": "null"},
                    ]
                },
            },
        }

        actual = TopLevelConstraintFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_model_constraint_properties_object_only(self) -> None:
        @forbid_if(["bar"], FieldEqCondition("baz", 42))
        @require_any_of("foo", "bar")
        class PropertiesObjectConstraintFeature(Feature):
            foo: Omitable[str]
            bar: Omitable[bool]
            baz: int

        expect = {
            "title": "PropertiesObjectConstraintFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {},
                "bbox": {},
                "geometry": {},
                "properties": {
                    "required": ["baz"],
                    "anyOf": [
                        {"required": ["foo"]},
                        {"required": ["bar"]},
                    ],
                    "if": {
                        "properties": {
                            "baz": {
                                "const": 42,
                            },
                        },
                    },
                    "then": {
                        "not": {"required": ["bar"]},
                    },
                },
            },
        }

        actual = PropertiesObjectConstraintFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")

    def test_model_constraint_mixed(self) -> None:
        @forbid_if(["foo", "type"], FieldEqCondition("properties", "ban.foo"))
        @require_if(["id", "foo", "qux"], FieldEqCondition("corge", 42))
        @require_any_of("bbox", "foo", "garply")
        class MixedConstraintFeature(Feature):
            foo: Omitable[bool]
            bar: bool
            baz: bool
            qux: Omitable[str]
            corge: int
            garply: Omitable[bool]
            type: Omitable[str]
            properties: str

        expect = {
            "title": "MixedConstraintFeature",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "type",
                "geometry",
                "properties",
            ],
            "anyOf": [
                {"required": ["bbox"]},
                {
                    "properties": {
                        "properties": {
                            "type": "object",
                            "required": ["foo"],
                        }
                    },
                },
                {
                    "properties": {
                        "properties": {
                            "type": "object",
                            "required": ["garply"],
                        },
                    },
                },
            ],
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "properties": {
                                "type": "object",
                                "properties": {
                                    "corge": {
                                        "const": 42,
                                    },
                                },
                            }
                        }
                    },
                    "then": {
                        "required": ["id"],
                        "properties": {
                            "properties": {
                                "type": "object",
                                "required": ["foo", "qux"],
                            },
                        },
                    },
                },
                {
                    "if": {
                        "properties": {
                            "properties": {
                                "type": "object",
                                "properties": {
                                    "properties": {
                                        "const": "ban.foo",
                                    },
                                },
                            }
                        },
                    },
                    "then": {
                        "not": {
                            "properties": {
                                "properties": {
                                    "type": "object",
                                    "required": ["foo", "type"],
                                }
                            }
                        },
                    },
                },
            ],
            "properties": {
                "type": {"const": "Feature", "type": "string"},
                "id": {
                    "type": "string",
                },
                "bbox": {
                    "type": "array",
                },
                "geometry": {},
                "properties": {
                    "type": "object",
                    "required": ["bar", "baz", "corge", "properties"],
                    "properties": {
                        "foo": {
                            "type": "boolean",
                        },
                        "bar": {
                            "type": "boolean",
                        },
                        "baz": {
                            "type": "boolean",
                        },
                        "qux": {
                            "type": "string",
                        },
                        "corge": {
                            "type": "integer",
                        },
                        "garply": {
                            "type": "boolean",
                        },
                        "type": {
                            "type": "string",
                        },
                        "properties": {
                            "type": "string",
                        },
                    },
                },
            },
        }

        actual = MixedConstraintFeature.model_json_schema()
        print(json.dumps(actual, indent=2))

        assert_subset(expect, actual, "expect", "actual")


class Test_FieldLevel:
    @pytest.mark.parametrize(
        "value",
        [
            True,
            False,
            {},
            {"$comment": "foo"},
            {"default": "bar"},
            {"deprecated": "baz"},
            {"description": "qux"},
            {"examples": "corge"},
            {"examples": {}},
            {"readOnly": True},
            {"writeOnly": True},
            {"title": "garply"},
            {"properties": {}},
            {"required": []},
            {"allOf": []},
            {"anyOf": []},
            {"oneOf": []},
            {"not": {}},
            {"if": {}},
            {"then": {}},
            {"else": {}},
            {
                "allOf": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
            {
                "anyOf": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
            {
                "anyOf": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
            {
                "oneOf": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
            {
                "not": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
            {
                "if": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
            {
                "then": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
            {
                "else": [
                    {"required": []},
                    {"properties": {}},
                ]
            },
        ],
    )
    def test_classify_unknown(self, value: JsonValue) -> None:
        actual = _FieldLevel.classify(Feature, value)

        assert _FieldLevel.UNKNOWN == actual

    @pytest.mark.parametrize(
        "value",
        [
            ["id", "foo"],
            ["bbox", "foo"],
            ["geometry", "foo"],
            ["bar", "baz", "id", "qux", "geometry", "bbox"],
            {"required": ["id", "foo"]},
            {
                "properties": {
                    "foo": {},
                    "bbox": {},
                }
            },
            {
                "required": ["id"],
                "properties": {
                    "foo": {},
                },
            },
            {"allOf": [{"required": ["id", "foo"]}]},
            {"anyOf": [{"required": ["id", "foo"]}]},
            {"oneOf": [{"required": ["id", "foo"]}]},
            {"not": {"required": ["id", "foo"]}},
            {"if": {"required": ["id", "foo"]}},
            {"then": {"required": ["id", "foo"]}},
            {"else": {"required": ["id", "foo"]}},
        ],
    )
    def test_classify_mixed(self, value: JsonValue) -> None:
        actual = _FieldLevel.classify(Feature, value)

        assert _FieldLevel.MIXED == actual

    @pytest.mark.parametrize(
        "value",
        [
            "foo",
            "properties",
            ["foo"],
            ("properties",),
            ["foo", "bar", "properties"],
            {"required": ["foo"]},
            {"required": ["properties"]},
            {"required": ["foo", "properties"]},
            {
                "properties": {
                    "foo": {"type": "object", "required": ["id", "bbox"]},
                }
            },
            {
                "required": ["foo", "bar"],
                "properties": {
                    "properties": {},
                    "baz": {},
                },
            },
            {"allOf": [{"required": ["foo"]}]},  # This one?
            {"anyOf": [{"required": ["foo"]}]},
            {"oneOf": [{"required": ["foo"]}]},
            {"not": {"required": ["foo"]}},
            {"if": {"required": ["foo"]}},
            {"then": {"required": ["foo"]}},
            {"else": {"required": ["foo"]}},
        ],
    )
    def test_classify_properties_object(self, value: JsonValue) -> None:
        actual = _FieldLevel.classify(Feature, value)

        assert _FieldLevel.PROPERTIES_OBJECT == actual

    @pytest.mark.parametrize(
        "value",
        [
            "id",
            "bbox",
            "geometry",
            ["id"],
            ("bbox",),
            ["geometry"],
            ("id", "bbox", "geometry"),
            {"required": ["id"]},
            {"required": ["bbox"]},
            {"required": ["bbox", "geometry"]},
            {
                "properties": {
                    "bbox": {"type": "object", "required": ["foo", "bar"]},
                }
            },
            {
                "required": ["id", "bbox"],
                "properties": {
                    "id": {},
                    "geometry": {},
                },
            },
            {"allOf": [{"required": ["id"]}]},
            {"anyOf": [{"required": ["bbox"]}]},
            {"oneOf": [{"required": ["geometry"]}]},
            {"not": {"required": ["id", "bbox"]}},
            {"if": {"required": ["bbox", "geometry"]}},
            {"then": {"required": ["id"]}},
            {"else": {"required": ["id"]}},
        ],
    )
    def test_classify_top_level_object(self, value: JsonValue) -> None:
        actual = _FieldLevel.classify(Feature, value)

        assert _FieldLevel.TOP_LEVEL_OBJECT == actual

    def test_classify_error_unsupported_keyword_deep(self) -> None:
        _ = _FieldLevel.classify(
            Feature,
            {
                "properties": {
                    "foo": {
                        "type": "object",
                        "minProperties": 1,
                    },
                    "bbox": {
                        "type": "object",
                        "minProperties": 2,
                    },
                }
            },
        )

    @pytest.mark.parametrize(
        "value",
        [
            {"minProperties": 1},
            {"allOf": [{"minProperties": 2}]},
            {"anyOf": [{"minProperties": 2}]},
            {"oneOf": [{"minProperties": 2}]},
            {"not": {"minProperties": 2}},
            {"allOf": [{"not": {"minProperties": 2}}]},
            {"anyOf": [{"not": {"minProperties": 2}}]},
            {"oneOf": [{"not": {"minProperties": 2}}]},
        ],
    )
    def test_classify_error_unsupported_keyword_shallow(self, value: JsonValue) -> None:
        with pytest.raises(ValueError, match="unsupported JSON Schema keyword '\\w+'"):
            _FieldLevel.classify(Feature, value)


class TestRefactoring:
    @pytest.mark.parametrize(
        "sub_schema,top_level_schema,properties_object_schema,expect_top_level_schema,expect_properties_object_schema",
        [
            ({}, {}, {}, None, None),
            (
                {"required": ["id"]},
                {},
                {},
                {"required": ["id"]},
                None,
            ),
            (
                {"required": ["foo"]},
                {},
                {},
                None,
                {"required": ["foo"]},
            ),
            (
                {"required": ["id", "foo"]},
                {},
                {},
                {
                    "required": ["id"],
                    "properties": {
                        "properties": {"type": "object", "required": ["foo"]}
                    },
                },
                None,
            ),
            (
                {
                    "anyOf": [
                        {"required": ["foo"]},
                        {"required": ["bar"]},
                    ]
                },
                {},
                {},
                None,
                {
                    "anyOf": [
                        {"required": ["foo"]},
                        {"required": ["bar"]},
                    ]
                },
            ),
            (
                {
                    "anyOf": [
                        {"required": ["id"]},
                        {"required": ["foo"]},
                    ]
                },
                {},
                {},
                {
                    "anyOf": [
                        {"required": ["id"]},
                        {
                            "properties": {
                                "properties": {
                                    "type": "object",
                                    "required": ["foo"],
                                },
                            },
                        },
                    ],
                },
                None,
            ),
            (
                {
                    "if": {
                        "required": ["id", "foo"],
                    },
                    "then": {
                        "allOf": [
                            {
                                "not": {
                                    "required": ["bbox", "bar"],
                                },
                            },
                            {
                                "properties": {
                                    "id": {"const": "hello"},
                                    "baz": {"const": 123},
                                },
                            },
                        ],
                    },
                    "else": {
                        "anyOf": [
                            {"required": ["bbox"]},
                            {"required": ["qux"]},
                        ],
                    },
                },
                {},
                {},
                {
                    "if": {
                        "properties": {
                            "properties": {
                                "type": "object",
                                "required": ["foo"],
                            },
                        },
                        "required": ["id"],
                    },
                    "then": {
                        "allOf": [
                            {
                                "not": {
                                    "required": ["bbox"],
                                    "properties": {
                                        "properties": {
                                            "type": "object",
                                            "required": ["bar"],
                                        },
                                    },
                                },
                            },
                            {
                                "properties": {
                                    "id": {
                                        "const": "hello",
                                    },
                                    "properties": {
                                        "type": "object",
                                        "properties": {
                                            "baz": {"const": 123},
                                        },
                                    },
                                },
                            },
                        ],
                    },
                    "else": {
                        "anyOf": [
                            {"required": ["bbox"]},
                            {
                                "properties": {
                                    "properties": {
                                        "type": "object",
                                        "required": ["qux"],
                                    },
                                },
                            },
                        ],
                    },
                },
                None,
            ),
        ],
    )
    def test_maybe_refactor_schema(
        self,
        sub_schema: JsonSchemaValue,
        top_level_schema: JsonSchemaValue,
        properties_object_schema: JsonSchemaValue,
        expect_top_level_schema: JsonSchemaValue | None,
        expect_properties_object_schema: JsonSchemaValue | None,
    ) -> None:
        _sub_schema = deepcopy(sub_schema)
        _top_level_schema = deepcopy(top_level_schema)
        _properties_object_schema = deepcopy(properties_object_schema)

        _maybe_refactor_schema(
            Feature, _sub_schema, _top_level_schema, _properties_object_schema
        )

        print(f"_top_level_schema => {repr(_top_level_schema)}")
        print(f"_properties_object_schema => {repr(_properties_object_schema)}")

        if expect_top_level_schema:
            assert expect_top_level_schema == _top_level_schema
        else:
            assert top_level_schema == _top_level_schema

        if expect_properties_object_schema:
            assert expect_properties_object_schema == _properties_object_schema
        else:
            assert properties_object_schema == _properties_object_schema
