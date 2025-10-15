import json

import pytest
from pydantic import ValidationError, create_model

from overture.schema.system.feature import Feature
from overture.schema.system.optionality import Omitable
from overture.schema.system.primitive import BBox, Geometry


class TestSerializeModel:
    @pytest.mark.parametrize(
        "feature,expect",
        [
            (
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
            ),
            (
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),
                {
                    "type": "Feature",
                    "id": "foo",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
            ),
            (
                Feature(
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
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),
                {
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
            ),
            (
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),
                {
                    "id": "foo",
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
            ),
            (
                Feature(
                    bbox=BBox(0, 1, 0, 2), geometry=Geometry.from_wkt("POINT(1 2)")
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
        sub_feature = SubFeature(id="foo", foo=42, geometry=geometry)

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
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),
            ),
            (
                {
                    "type": "Feature",
                    "id": "foo",
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),
            ),
            (
                {
                    "type": "Feature",
                    "bbox": [0, 1, 0, 2],
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    "properties": {},
                },
                Feature(
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
                Feature(geometry=Geometry.from_wkt("POINT(1 2)")),
            ),
            (
                {
                    "id": "foo",
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
                Feature(id="foo", geometry=Geometry.from_wkt("POINT(1 2)")),
            ),
            (
                {
                    "bbox": BBox(0, 1, 0, 2),
                    "geometry": Geometry.from_wkt("POINT(1 2)"),
                },
                Feature(
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
        expect = SubFeature(id="Hello", foo=42, baz=None, bbox=bbox, geometry=geometry)

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

    def test_error_data_not_dict(self) -> None:
        with pytest.raises(
            TypeError, match="feature data must be a `dict`, but 'foo' is a `str`"
        ):
            Feature.model_validate("foo")

        with pytest.raises(
            TypeError, match="feature data must be a `dict`, but 'bar' is a `str`"
        ):
            Feature.model_validate_json('"bar"')

    @pytest.mark.parametrize(
        "feature_class,missing_field,json_input,python_input",
        [
            (
                Feature,
                "geometry",
                {"type": "Feature"},
                {},
            ),
            (
                Feature,
                "geometry",
                {"type": "Feature", "id": "foo", "bbox": [1, 2, 3, 4]},
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
                },
                {
                    "geometry": Geometry.from_wkt("POINT(0 0)"),
                },
            ),
        ],
    )
    def test_error_type_property_missing(
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
                {"type": "Feature", "geometry": "foo"},
                {"geometry": "foo"},
            ),
            (
                Feature,
                "id",
                {"type": "Feature", "geometry": {"type":"Point","coordinates":[0,0]}, "id": 1.5},
                {"geometry": Geometry.from_wkt("POINT(0 0)"), "id": 1.5},
            ),
            (
                Feature,
                "bbox",
                {"type": "Feature", "geometry": {"type":"Point","coordinates":[0,0]}, "id": "foo", "bbox": "bar"},
                {"geometry": Geometry.from_wkt("POINT(0 0)"), "id": "foo", "bbox": "bar"},
            ),
            (
                create_model('SubFeature', __base__=Feature, foo=int),
                'foo',
                {"type": "Feature", "geometry": {"type":"Point","coordinates":[0,0]}, "properties":{"foo":"bar"}},
                {"geometry": Geometry.from_wkt("POINT(0 0)"), "foo": "bar"},
            )
        ],
    )
    def test_error_type_property_wrong_value(
        self,
        feature_class: type[Feature],
        invalid_field: str,
        json_input: dict[str, object],
        python_input: dict[str, object],
    ) -> None:
        def assert_wrong_value(kind: str, input: dict[str, object], error_info: pytest.ExceptionInfo) -> None:
            validation_error = error_info.value
            first_error = validation_error.errors()[0]
            assert first_error["type"] in { 'value_error', 'string_type', 'int_parsing' }, f"unexpected error type {repr(first_error['type'])} for {kind} input {repr(input)}"
            assert invalid_field == first_error["loc"][0], f"unexpected field name {repr(first_error['loc'][0])} for {kind} input {repr(input)}"

        with pytest.raises(ValidationError) as json_error_info:
            feature_class.model_validate_json(json.dumps(json_input))

        assert_wrong_value('json', json_input, json_error_info)

        with pytest.raises(ValidationError) as python_error_info:
            feature_class.model_validate(python_input)

        assert_wrong_value('python', python_input, python_error_info)

    def test_error_properties_missing(self) -> None:
        pass

    def test_error_properties_not_object_or_null(self) -> None:
        pass

    def test_error_illegal_root_properties(self) -> None:
        pass

    def test_error_illegal_properties(self) -> None:
        pass

    def test_error_missing_required_property(self) -> None:
        # TODO: both basic and advanced subclass
        pass

    def test_error_extra_property_not_allowed(self) -> None:
        pass
