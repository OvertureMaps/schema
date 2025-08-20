from collections.abc import Mapping
from typing import Any

import pytest
from overture.schema.core.bbox import BBox
from overture.schema.core.geometry import Geometry
from overture.schema.core.models import Feature
from shapely.geometry import LineString, Point


def prune_dict(data: dict[str, Any] | tuple | list, remove_list: tuple[str, ...]) -> None:
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
    prune_dict(data, ('title', 'description'))
    return data

def test_feature_json_schema() -> None:
    actual = prune_json_schema(Feature.model_json_schema())

    expect = {
    '$defs': {
        'SourcePropertyItem': {
            'additionalProperties': False,
            'properties': {
                'between': {
                    'anyOf': [
                        {
                            'items': {
                                'maximum': 1.0,
                                'minimum': 0.0,
                                'type': 'number',
                            },
                            'maxItems': 2,
                            'minItems': 2,
                            'type': 'array',
                        },
                        {
                            'type': 'null',
                        },
                    ],
                    'default': None,
                },
                'confidence': {
                    'anyOf': [
                        {
                            'maximum': 1.0,
                            'minimum': 0.0,
                            'type': 'number',
                        },
                        {
                            'type': 'null',
                        },
                    ],
                    'default': None,
                },
                'dataset': {
                    'type': 'string',
                },
                'property': {
                    'type': 'string',
                },
                'record_id': {
                    'anyOf': [
                        {
                            'type': 'string',
                        },
                        {
                            'type': 'null',
                        },
                    ],
                    'default': None,
                },
                'update_time': {
                    'anyOf': [
                        {
                            'format': 'date-time',
                            'pattern': '^([1-9]\\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01])T([01]\\d|2[0-3]):([0-5]\\d):([0-5]\\d|60)(\\.\\d{1,3})?(Z|[-+]([01]\\d|2[0-3]):[0-5]\\d)$',
                            'type': 'string',
                        },
                        {
                            'type': 'null',
                        },
                    ],
                    'default': None,
                },
            },
            'required': [
                'property',
                'dataset',
            ],
            'type': 'object',
        },
    },
    'additionalProperties': False,
    'patternProperties': {
        '^ext_.*$': {},
    },
    'properties': {
        'bbox': {
            'anyOf': [
                {
                    'items': {
                        'type': 'number',
                    },
                    'minItems': 4,
                    'maxItems': 4,
                    'type': 'array',
                },
                {
                    'type': 'null',
                },
            ],
            'default': None,
        },
        'geometry': {
            'oneOf': [
                {
                    'properties': {
                        'bbox': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 4,
                            'type': 'array',
                        },
                        'geometries': {
                            'oneOf': [
                                {
                                    'properties': {
                                        'bbox': {
                                            'items': {
                                                'type': 'number',
                                            },
                                            'minItems': 4,
                                            'type': 'array',
                                        },
                                        'coordinates': {
                                            'items': {
                                                'items': {
                                                    'type': 'number',
                                                },
                                                'minItems': 2,
                                                'type': 'array',
                                            },
                                            'minItems': 2,
                                            'type': 'array',
                                        },
                                        'type': {
                                            'const': 'LineString',
                                            'type': 'string',
                                        },
                                    },
                                    'required': [
                                        'type',
                                        'coordinates',
                                    ],
                                    'type': 'object',
                                },
                                {
                                    'properties': {
                                        'bbox': {
                                            'items': {
                                                'type': 'number',
                                            },
                                            'minItems': 4,
                                            'type': 'array',
                                        },
                                        'coordinates': {
                                            'items': {
                                                'type': 'number',
                                            },
                                            'minItems': 2,
                                            'type': 'array',
                                        },
                                        'type': {
                                            'const': 'Point',
                                            'type': 'string',
                                        },
                                    },
                                    'required': [
                                        'type',
                                        'coordinates',
                                    ],
                                    'type': 'object',
                                },
                                {
                                    'properties': {
                                        'bbox': {
                                            'items': {
                                                'type': 'number',
                                            },
                                            'minItems': 4,
                                            'type': 'array',
                                        },
                                        'coordinates': {
                                            'items': {
                                                'items': {
                                                    'items': {
                                                        'type': 'number',
                                                    },
                                                    'minItems': 2,
                                                    'type': 'array',
                                                },
                                                'minItems': 4,
                                                'type': 'array',
                                            },
                                            'minItems': 1,
                                            'type': 'array',
                                        },
                                        'type': {
                                            'const': 'Polygon',
                                            'type': 'string',
                                        },
                                    },
                                    'required': [
                                        'type',
                                        'coordinates',
                                    ],
                                    'type': 'object',
                                },
                                {
                                    'properties': {
                                        'bbox': {
                                            'items': {
                                                'type': 'number',
                                            },
                                            'minItems': 4,
                                            'type': 'array',
                                        },
                                        'coordinates': {
                                            'items': {
                                                'items': {
                                                    'items': {
                                                        'type': 'number',
                                                    },
                                                    'minItems': 2,
                                                    'type': 'array',
                                                },
                                                'minItems': 2,
                                                'type': 'array',
                                            },
                                            'minItems': 1,
                                            'type': 'array',
                                        },
                                        'type': {
                                            'const': 'MultiLineString',
                                            'type': 'string',
                                        },
                                    },
                                    'required': [
                                        'type',
                                        'coordinates',
                                    ],
                                    'type': 'object',
                                },
                                {
                                    'properties': {
                                        'bbox': {
                                            'items': {
                                                'type': 'number',
                                            },
                                            'minItems': 4,
                                            'type': 'array',
                                        },
                                        'coordinates': {
                                            'items': {
                                                'items': {
                                                    'type': 'number',
                                                },
                                                'minItems': 2,
                                                'type': 'array',
                                            },
                                            'minItems': 1,
                                            'type': 'array',
                                        },
                                        'type': {
                                            'const': 'MultiPoint',
                                            'type': 'string',
                                        },
                                    },
                                    'required': [
                                        'type',
                                        'coordinates',
                                    ],
                                    'type': 'object',
                                },
                                {
                                    'properties': {
                                        'bbox': {
                                            'items': {
                                                'type': 'number',
                                            },
                                            'minItems': 4,
                                            'type': 'array',
                                        },
                                        'coordinates': {
                                            'items': {
                                                'items': {
                                                    'items': {
                                                        'items': {
                                                            'type': 'number',
                                                        },
                                                        'minItems': 2,
                                                        'type': 'array',
                                                    },
                                                    'minItems': 4,
                                                    'type': 'array',
                                                },
                                                'minItems': 1,
                                                'type': 'array',
                                            },
                                            'minItems': 1,
                                            'type': 'array',
                                        },
                                        'type': {
                                            'const': 'MultiPolygon',
                                            'type': 'string',
                                        },
                                    },
                                    'required': [
                                        'type',
                                        'coordinates',
                                    ],
                                    'type': 'object',
                                },
                            ],
                        },
                        'type': {
                            'const': 'GeometryCollection',
                            'type': 'string',
                        },
                    },
                    'required': [
                        'type',
                        'geometries',
                    ],
                    'type': 'object',
                },
                {
                    'properties': {
                        'bbox': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 4,
                            'type': 'array',
                        },
                        'coordinates': {
                            'items': {
                                'items': {
                                    'type': 'number',
                                },
                                'minItems': 2,
                                'type': 'array',
                            },
                            'minItems': 2,
                            'type': 'array',
                        },
                        'type': {
                            'const': 'LineString',
                            'type': 'string',
                        },
                    },
                    'required': [
                        'type',
                        'coordinates',
                    ],
                    'type': 'object',
                },
                {
                    'properties': {
                        'bbox': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 4,
                            'type': 'array',
                        },
                        'coordinates': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 2,
                            'type': 'array',
                        },
                        'type': {
                            'const': 'Point',
                            'type': 'string',
                        },
                    },
                    'required': [
                        'type',
                        'coordinates',
                    ],
                    'type': 'object',
                },
                {
                    'properties': {
                        'bbox': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 4,
                            'type': 'array',
                        },
                        'coordinates': {
                            'items': {
                                'items': {
                                    'items': {
                                        'type': 'number',
                                    },
                                    'minItems': 2,
                                    'type': 'array',
                                },
                                'minItems': 4,
                                'type': 'array',
                            },
                            'minItems': 1,
                            'type': 'array',
                        },
                        'type': {
                            'const': 'Polygon',
                            'type': 'string',
                        },
                    },
                    'required': [
                        'type',
                        'coordinates',
                    ],
                    'type': 'object',
                },
                {
                    'properties': {
                        'bbox': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 4,
                            'type': 'array',
                        },
                        'coordinates': {
                            'items': {
                                'items': {
                                    'items': {
                                        'type': 'number',
                                    },
                                    'minItems': 2,
                                    'type': 'array',
                                },
                                'minItems': 2,
                                'type': 'array',
                            },
                            'minItems': 1,
                            'type': 'array',
                        },
                        'type': {
                            'const': 'MultiLineString',
                            'type': 'string',
                        },
                    },
                    'required': [
                        'type',
                        'coordinates',
                    ],
                    'type': 'object',
                },
                {
                    'properties': {
                        'bbox': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 4,
                            'type': 'array',
                        },
                        'coordinates': {
                            'items': {
                                'items': {
                                    'type': 'number',
                                },
                                'minItems': 2,
                                'type': 'array',
                            },
                            'minItems': 1,
                            'type': 'array',
                        },
                        'type': {
                            'const': 'MultiPoint',
                            'type': 'string',
                        },
                    },
                    'required': [
                        'type',
                        'coordinates',
                    ],
                    'type': 'object',
                },
                {
                    'properties': {
                        'bbox': {
                            'items': {
                                'type': 'number',
                            },
                            'minItems': 4,
                            'type': 'array',
                        },
                        'coordinates': {
                            'items': {
                                'items': {
                                    'items': {
                                        'items': {
                                            'type': 'number',
                                        },
                                        'minItems': 2,
                                        'type': 'array',
                                    },
                                    'minItems': 4,
                                    'type': 'array',
                                },
                                'minItems': 1,
                                'type': 'array',
                            },
                            'minItems': 1,
                            'type': 'array',
                        },
                        'type': {
                            'const': 'MultiPolygon',
                            'type': 'string',
                        },
                    },
                    'required': [
                        'type',
                        'coordinates',
                    ],
                    'type': 'object',
                },
            ],
        },
        'id': {
            'minLength': 1,
            'pattern': '^\\S+$',
            'type': 'string',
        },
        'properties': {
            'additionalProperties': False,
            'patternProperties': {
                '^ext_.*$': {},
            },
            'properties': {
                'sources': {
                    'anyOf': [
                        {
                            'items': {
                                '$ref': '#/$defs/SourcePropertyItem',
                            },
                            'minItems': 1,
                            'type': 'array',
                            'uniqueItems': True,
                        },
                        {
                            'type': 'null',
                        },
                    ],
                    'default': None,
                },
                'theme': {
                    'type': 'string',
                },
                'type': {
                    'type': 'string',
                },
                'version': {
                    'minimum': 0,
                    'type': 'integer',
                },
            },
            'required': [
                'theme',
                'type',
                'version',
            ],
            'type': 'object',
            'unevaluatedProperties': False,
        },
        'type': {
            'const': 'Feature',
            'type': 'string',
        },
    },
    'required': [
        'id',
        'geometry',
        'properties',
        'type',
    ],
    'type': 'object',
}

    assert actual == expect


@pytest.mark.parametrize("feature, expect", [
    (
        Feature(
            id = "foo",
            theme = "bar",
            type = "baz",
            geometry = Geometry(Point(-1, 1)),
            version = 1,
        ),
        {
            'type': 'Feature',
            'id': 'foo',
            'bbox': None,
            'geometry': {
                'type': 'Point',
                'coordinates': [-1, 1],
            },
            'properties': {
                'theme': 'bar',
                'type': 'baz',
                'version': 1,
                'sources': None,
            }
        },
    ),

    (
        Feature(
            id = "foo",
            theme = "bar",
            type = "baz",
            bbox = BBox(0, 0, 1, 1),
            geometry = Geometry(LineString(((0, 0), (1, 1)))),
            version = 2,
        ),
        {
            'type': 'Feature',
            'id': 'foo',
            'bbox': [0, 0, 1, 1],
            'geometry': {
                'type': 'LineString',
                'coordinates': [
                    [0, 0],
                    [1, 1],
                ]
            },
            'properties': {
                'theme': 'bar',
                'type': 'baz',
                'version': 2,
                'sources': None,
            }
        },
    ),
])
def test_feature_json(feature: Feature, expect: dict[str, Any]) -> None:
    assert feature.model_dump(mode = 'json') == expect
