from collections.abc import Mapping
from typing import Any

import pytest
from deepdiff import DeepDiff
from overture.schema.core.bbox import BBox
from overture.schema.core.geometry import Geometry
from overture.schema.core.models import Feature
from shapely.geometry import LineString, Point


def prune_dict(
    data: dict[str, Any] | tuple | list, remove_list: tuple[str, ...]
) -> None:
    if isinstance(data, Mapping):
        keys_to_remove = [k for k in data if k in remove_list]
        for k in keys_to_remove:
            data.pop(k)
        for v in data.values():
            prune_dict(v, remove_list)
    elif isinstance(data, tuple | list):
        for item in data:
            prune_dict(item, remove_list)


def prune_json_schema(data: dict[str, Any]) -> dict[str, Any]:
    prune_dict(data, ("title", "description"))
    return data


def test_feature_json_schema() -> None:
    actual = prune_json_schema(Feature.model_json_schema())

    expect = {
        "$defs": {
            "SourcePropertyItem": {
                "additionalProperties": False,
                "properties": {
                    "between": {
                        "anyOf": [
                            {
                                "items": {
                                    "maximum": 1.0,
                                    "minimum": 0.0,
                                    "type": "number",
                                },
                                "maxItems": 2,
                                "minItems": 2,
                                "type": "array",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                    },
                    "property": {"type": "string"},
                    "dataset": {"type": "string"},
                    "license": {
                        "anyOf": [
                            {
                                "pattern": "^(\\S.*)?\\S$",
                                "type": "string",
                            },
                            {
                                "type": "null",
                            },
                        ],
                        "default": None,
                    },
                    "record_id": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": None,
                    },
                    "update_time": {
                        "anyOf": [
                            {
                                "format": "date-time",
                                "pattern": "^([1-9]\\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01])T([01]\\d|2[0-3]):([0-5]\\d):([0-5]\\d|60)(\\.\\d{1,3})?(Z|[-+]([01]\\d|2[0-3]):[0-5]\\d)$",
                                "type": "string",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                    },
                    "confidence": {
                        "anyOf": [
                            {"maximum": 1.0, "minimum": 0.0, "type": "number"},
                            {"type": "null"},
                        ],
                        "default": None,
                    },
                },
                "required": ["property", "dataset"],
                "type": "object",
            }
        },
        "additionalProperties": False,
        "patternProperties": {"^ext_.*$": {}},
        "properties": {
            "id": {"minLength": 1, "pattern": "^\\S+$", "type": "string"},
            "geometry": {
                "oneOf": [
                    {
                        "properties": {
                            "type": {"const": "GeometryCollection", "type": "string"},
                            "bbox": {
                                "items": {"type": "number"},
                                "minItems": 4,
                                "type": "array",
                            },
                            "geometries": {
                                "oneOf": [
                                    {
                                        "properties": {
                                            "type": {
                                                "const": "LineString",
                                                "type": "string",
                                            },
                                            "bbox": {
                                                "items": {"type": "number"},
                                                "minItems": 4,
                                                "type": "array",
                                            },
                                            "coordinates": {
                                                "items": {
                                                    "items": {"type": "number"},
                                                    "maxItems": 3,
                                                    "minItems": 2,
                                                    "type": "array",
                                                },
                                                "minItems": 2,
                                                "type": "array",
                                            },
                                        },
                                        "required": ["type", "coordinates"],
                                        "type": "object",
                                    },
                                    {
                                        "properties": {
                                            "type": {
                                                "const": "Point",
                                                "type": "string",
                                            },
                                            "bbox": {
                                                "items": {"type": "number"},
                                                "minItems": 4,
                                                "type": "array",
                                            },
                                            "coordinates": {
                                                "items": {"type": "number"},
                                                "maxItems": 3,
                                                "minItems": 2,
                                                "type": "array",
                                            },
                                        },
                                        "required": ["type", "coordinates"],
                                        "type": "object",
                                    },
                                    {
                                        "properties": {
                                            "type": {
                                                "const": "Polygon",
                                                "type": "string",
                                            },
                                            "bbox": {
                                                "items": {"type": "number"},
                                                "minItems": 4,
                                                "type": "array",
                                            },
                                            "coordinates": {
                                                "items": {
                                                    "items": {
                                                        "items": {"type": "number"},
                                                        "maxItems": 3,
                                                        "minItems": 2,
                                                        "type": "array",
                                                    },
                                                    "minItems": 4,
                                                    "type": "array",
                                                },
                                                "minItems": 1,
                                                "type": "array",
                                            },
                                        },
                                        "required": ["type", "coordinates"],
                                        "type": "object",
                                    },
                                    {
                                        "properties": {
                                            "type": {
                                                "const": "MultiLineString",
                                                "type": "string",
                                            },
                                            "bbox": {
                                                "items": {"type": "number"},
                                                "minItems": 4,
                                                "type": "array",
                                            },
                                            "coordinates": {
                                                "items": {
                                                    "items": {
                                                        "items": {"type": "number"},
                                                        "maxItems": 3,
                                                        "minItems": 2,
                                                        "type": "array",
                                                    },
                                                    "minItems": 2,
                                                    "type": "array",
                                                },
                                                "minItems": 1,
                                                "type": "array",
                                            },
                                        },
                                        "required": ["type", "coordinates"],
                                        "type": "object",
                                    },
                                    {
                                        "properties": {
                                            "type": {
                                                "const": "MultiPoint",
                                                "type": "string",
                                            },
                                            "bbox": {
                                                "items": {"type": "number"},
                                                "minItems": 4,
                                                "type": "array",
                                            },
                                            "coordinates": {
                                                "items": {
                                                    "items": {"type": "number"},
                                                    "maxItems": 3,
                                                    "minItems": 2,
                                                    "type": "array",
                                                },
                                                "minItems": 1,
                                                "type": "array",
                                            },
                                        },
                                        "required": ["type", "coordinates"],
                                        "type": "object",
                                    },
                                    {
                                        "properties": {
                                            "type": {
                                                "const": "MultiPolygon",
                                                "type": "string",
                                            },
                                            "bbox": {
                                                "items": {"type": "number"},
                                                "minItems": 4,
                                                "type": "array",
                                            },
                                            "coordinates": {
                                                "items": {
                                                    "items": {
                                                        "items": {
                                                            "items": {"type": "number"},
                                                            "maxItems": 3,
                                                            "minItems": 2,
                                                            "type": "array",
                                                        },
                                                        "minItems": 4,
                                                        "type": "array",
                                                    },
                                                    "minItems": 1,
                                                    "type": "array",
                                                },
                                                "minItems": 1,
                                                "type": "array",
                                            },
                                        },
                                        "required": ["type", "coordinates"],
                                        "type": "object",
                                    },
                                ]
                            },
                        },
                        "required": ["type", "geometries"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "type": {"const": "LineString", "type": "string"},
                            "bbox": {
                                "items": {"type": "number"},
                                "minItems": 4,
                                "type": "array",
                            },
                            "coordinates": {
                                "items": {
                                    "items": {"type": "number"},
                                    "maxItems": 3,
                                    "minItems": 2,
                                    "type": "array",
                                },
                                "minItems": 2,
                                "type": "array",
                            },
                        },
                        "required": ["type", "coordinates"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "type": {"const": "MultiLineString", "type": "string"},
                            "bbox": {
                                "items": {"type": "number"},
                                "minItems": 4,
                                "type": "array",
                            },
                            "coordinates": {
                                "items": {
                                    "items": {
                                        "items": {"type": "number"},
                                        "maxItems": 3,
                                        "minItems": 2,
                                        "type": "array",
                                    },
                                    "minItems": 2,
                                    "type": "array",
                                },
                                "minItems": 1,
                                "type": "array",
                            },
                        },
                        "required": ["type", "coordinates"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "type": {"const": "MultiPoint", "type": "string"},
                            "bbox": {
                                "items": {"type": "number"},
                                "minItems": 4,
                                "type": "array",
                            },
                            "coordinates": {
                                "items": {
                                    "items": {"type": "number"},
                                    "maxItems": 3,
                                    "minItems": 2,
                                    "type": "array",
                                },
                                "minItems": 1,
                                "type": "array",
                            },
                        },
                        "required": ["type", "coordinates"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "type": {"const": "MultiPolygon", "type": "string"},
                            "bbox": {
                                "items": {"type": "number"},
                                "minItems": 4,
                                "type": "array",
                            },
                            "coordinates": {
                                "items": {
                                    "items": {
                                        "items": {
                                            "items": {"type": "number"},
                                            "maxItems": 3,
                                            "minItems": 2,
                                            "type": "array",
                                        },
                                        "minItems": 4,
                                        "type": "array",
                                    },
                                    "minItems": 1,
                                    "type": "array",
                                },
                                "minItems": 1,
                                "type": "array",
                            },
                        },
                        "required": ["type", "coordinates"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "type": {"const": "Point", "type": "string"},
                            "bbox": {
                                "items": {"type": "number"},
                                "minItems": 4,
                                "type": "array",
                            },
                            "coordinates": {
                                "items": {"type": "number"},
                                "maxItems": 3,
                                "minItems": 2,
                                "type": "array",
                            },
                        },
                        "required": ["type", "coordinates"],
                        "type": "object",
                    },
                    {
                        "properties": {
                            "type": {"const": "Polygon", "type": "string"},
                            "bbox": {
                                "items": {"type": "number"},
                                "minItems": 4,
                                "type": "array",
                            },
                            "coordinates": {
                                "items": {
                                    "items": {
                                        "items": {"type": "number"},
                                        "maxItems": 3,
                                        "minItems": 2,
                                        "type": "array",
                                    },
                                    "minItems": 4,
                                    "type": "array",
                                },
                                "minItems": 1,
                                "type": "array",
                            },
                        },
                        "required": ["type", "coordinates"],
                        "type": "object",
                    },
                ],
            },
            "bbox": {
                "anyOf": [
                    {
                        "items": {"type": "number"},
                        "maxItems": 4,
                        "minItems": 4,
                        "type": "array",
                    },
                    {"type": "null"},
                ],
                "default": None,
            },
            "properties": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "type": {"type": "string"},
                    "version": {"maximum": 2147483647, "minimum": 0, "type": "integer"},
                    "sources": {
                        "anyOf": [
                            {
                                "items": {"$ref": "#/$defs/SourcePropertyItem"},
                                "minItems": 1,
                                "type": "array",
                                "uniqueItems": True,
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                    },
                },
                "unevaluatedProperties": False,
                "required": ["theme", "type", "version"],
                "patternProperties": {"^ext_.*$": {}},
                "additionalProperties": False,
            },
            "type": {"const": "Feature", "type": "string"},
        },
        "required": ["id", "geometry", "properties", "type"],
        "type": "object",
    }

    diff = DeepDiff(actual, expect, ignore_order=True)

    assert diff == {}


@pytest.mark.parametrize(
    "feature, expect",
    [
        (
            Feature(
                id="foo",
                theme="bar",
                type="baz",
                geometry=Geometry(Point(-1, 1)),
                version=1,
            ),
            {
                "type": "Feature",
                "id": "foo",
                "bbox": None,
                "geometry": {
                    "type": "Point",
                    "coordinates": [-1, 1],
                },
                "properties": {
                    "theme": "bar",
                    "type": "baz",
                    "version": 1,
                    "sources": None,
                },
            },
        ),
        (
            Feature(
                id="foo",
                theme="bar",
                type="baz",
                bbox=BBox(0, 0, 1, 1),
                geometry=Geometry(LineString(((0, 0), (1, 1)))),
                version=2,
            ),
            {
                "type": "Feature",
                "id": "foo",
                "bbox": [0, 0, 1, 1],
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [0, 0],
                        [1, 1],
                    ],
                },
                "properties": {
                    "theme": "bar",
                    "type": "baz",
                    "version": 2,
                    "sources": None,
                },
            },
        ),
    ],
)
def test_feature_json(feature: Feature, expect: dict[str, Any]) -> None:
    assert feature.model_dump(mode="json") == expect
