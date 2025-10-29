import json
from collections.abc import Mapping
from typing import Any

import pytest
from deepdiff import DeepDiff
from overture.schema.core.json_schema import EnhancedJsonSchemaGenerator
from overture.schema.core.models import OvertureFeature
from overture.schema.system.primitive import (
    BBox,
    Geometry,
)
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
    actual = prune_json_schema(
        OvertureFeature.model_json_schema(schema_generator=EnhancedJsonSchemaGenerator)
    )
    print(json.dumps(actual, indent=2))

    expect = {
        "$defs": {
            "SourceItem": {
                "additionalProperties": False,
                "properties": {
                    "between": {
                        "items": {
                            "maximum": 1.0,
                            "minimum": 0.0,
                            "type": "number",
                        },
                        "maxItems": 2,
                        "minItems": 2,
                        "type": "array",
                    },
                    "property": {"type": "string"},
                    "dataset": {"type": "string"},
                    "license": {
                        "pattern": "^(\\S.*)?\\S$",
                        "type": "string",
                    },
                    "record_id": {"type": "string"},
                    "update_time": {
                        "format": "date-time",
                        "type": "string",
                    },
                    "confidence": {"maximum": 1.0, "minimum": 0.0, "type": "number"},
                },
                "required": ["property", "dataset"],
                "type": "object",
            }
        },
        "additionalProperties": False,
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
                "items": {"type": "number"},
                "maxItems": 4,
                "minItems": 4,
                "type": "array",
            },
            "properties": {
                "type": "object",
                "not": {"required": ["id", "bbox", "geometry"]},
                "properties": {
                    "theme": {"type": "string"},
                    "type": {"type": "string"},
                    "version": {"maximum": 2147483647, "minimum": 0, "type": "integer"},
                    "sources": {
                        "items": {"$ref": "#/$defs/SourceItem"},
                        "minItems": 1,
                        "type": "array",
                        "uniqueItems": True,
                    },
                },
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
            OvertureFeature(  # type: ignore[call-arg]
                id="foo",
                theme="bar",
                type="baz",
                geometry=Geometry(Point(-1, 1)),
                version=1,
            ),
            {
                "type": "Feature",
                "id": "foo",
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
            OvertureFeature(
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
def test_feature_json(feature: OvertureFeature, expect: dict[str, Any]) -> None:
    assert feature.model_dump(mode="json") == expect
