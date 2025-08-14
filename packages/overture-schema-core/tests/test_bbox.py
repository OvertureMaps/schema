from typing import Any

import jsonpath_ng  # type: ignore[import-untyped]
import pytest
from overture.schema.core.bbox import BBox, Dim
from pydantic import BaseModel, ValidationError


def test_dim_construct_invalid_type() -> None:
    with pytest.raises(TypeError):
        Dim('foo', 1)   # type: ignore[arg-type]

    with pytest.raises(TypeError):
        Dim(1, 'bar')   # type: ignore[arg-type]


@pytest.mark.parametrize("min, max", [
    (0, 0),
    (1.5, 1),
    (1, 2.5),
])
def test_dim_construct_valid(min: float | int, max: float | int) -> None:
    dim = Dim(min, max)

    assert dim.min is min
    assert dim.max is max


@pytest.mark.parametrize("xmin, ymin, xmax, ymax, more", [
    ('foo', 2, 3, 4, ()),
    (1, 'foo', 3, 4, ()),
    (1, 2, 'foo', 4, ()),
    (1, 2, 3, 'foo', ()),
    (1, 2, 3, 4, 5),
    (1, 2, 3, 4, (5)),
])
def test_bbox_construct_invalid_type(xmin: Any, ymin: Any, xmax: Any, ymax: Any, more: Any) -> None:
    with pytest.raises(TypeError):
        BBox(xmin, ymin, xmax, ymax, more)


def test_bbox_construct_positional_no_more() -> None:
    bbox = BBox(1, 2, 3, 4.0)

    assert bbox.xmin == 1
    assert bbox.ymin == 2
    assert bbox.xmax == 3
    assert bbox.ymax == 4.0
    assert bbox.more == ()


def test_bbox_construct_positional_more() -> None:
    more = (Dim(5.0, 6.0),)
    bbox = BBox(1, 2, 3, 4.0, more)

    assert bbox.xmin == 1
    assert bbox.ymin == 2
    assert bbox.xmax == 3
    assert bbox.ymax == 4.0
    assert bbox.more is more


def test_bbox_construct_keyword_no_more() -> None:
    bbox = BBox(xmin=1.0, ymin=2.0, xmax=3.0, ymax=4)

    assert bbox.xmin == 1.0
    assert bbox.ymin == 2.0
    assert bbox.xmax == 3.0
    assert bbox.ymax == 4
    assert bbox.more == ()


def test_bbox_construct_keyword_more() -> None:
    more = (Dim(5.0, 6.0), Dim(7, 8))
    bbox = BBox(xmin=1.0, ymin=2.0, xmax=3.0, ymax=4, more=more)

    assert bbox.xmin == 1.0
    assert bbox.ymin == 2.0
    assert bbox.xmax == 3.0
    assert bbox.ymax == 4
    assert bbox.more is more


@pytest.mark.parametrize("bbox, expect", [
    (BBox(1, 2, 3, 4), (1, 2, 3, 4)),
    (BBox(xmin=0.0, ymin=1.5, xmax=0.0, ymax=2, more=(Dim(3, 4),)), (0.0, 1.5, 3, 0.0, 2, 4)),
    (BBox(-11.5, -12.5, 13.5, 14.5, (Dim(0, 1), Dim(-1, -2))), (-11.5, -12.5, 0, -1, 13.5, 14.5, 1, -2)),
])
def test_bbox_to_geo_json(bbox: BBox, expect: tuple[float | int, ...]) -> None:
    actual = bbox.to_geo_json()

    assert actual == expect


@pytest.mark.parametrize("geo_json, expect", [
    ([1, 2, 3, 4], BBox(1, 2, 3, 4)),
    ((1, 2, 3, 4, 5, 6), BBox(1, 2, 4, 5, (Dim(3, 6),))),
    ((1, 2, 3, 4, 5, 6, 7, 8), BBox(1, 2, 5, 6, (Dim(3, 7), Dim(4, 8)))),
])
def test_bbox_from_geo_json_success(geo_json: tuple[float | int, ...], expect: BBox) -> None:
    actual = BBox.from_geo_json(geo_json)

    assert actual == expect



@pytest.mark.parametrize("geo_json", [
    (1),
    ({}),
    ((1, 2, 3, 'foo'))
])
def test_bbox_from_geo_json_type_error(geo_json: tuple[float | int, ...]) -> None:
    with pytest.raises(TypeError):
        BBox.from_geo_json(geo_json)


@pytest.mark.parametrize("geo_json", [
    (()),
    ((1,)),
    ((1, 2)),
    ((1, 2, 3)),
    ((1, 2, 3, 4, 5,)),
    ((1, 2, 3, 4, 5, 6, 7)),
])
def test_bbox_from_geo_json_value_error(geo_json: tuple[float | int, ...]) -> None:
    with pytest.raises(ValueError):
        BBox.from_geo_json(geo_json)


def test_pydantic_json() -> None:
    class TestModel(BaseModel):
        bbox: BBox

    bbox = BBox(1, 2, 3, 4)
    test_model = TestModel(bbox = bbox)

    expect = {
        'bbox': [1, 2, 3, 4],
    }

    assert test_model.model_dump(mode = 'json') == expect


@pytest.mark.parametrize("input, expect", [
    ((1, 2, 3, 4), BBox(xmin=1, ymin=2, xmax=3, ymax=4)),
    ([1, 2, 3, 4, 5, 6], BBox(xmin=1, ymin=2, xmax=4, ymax=5, more=(Dim(3, 6),))),
    (BBox(0, -1, -2, 3), BBox(0, -1, -2, 3)),
])
def test_pydantic_validation_success(input: Any, expect: BBox) -> None:
    class TestModel(BaseModel):
        bbox: BBox

    test_model = TestModel(bbox = input)

    assert test_model.bbox == expect


@pytest.mark.parametrize("input", [
    'foo',
])
def test_pydantic_validation_error(input: Any) -> None:
    class TestModel(BaseModel):
        bbox: BBox

    with pytest.raises(ValidationError):
        TestModel(bbox = input)


def test_pydantic_json_schema() -> None:
    class TestModel(BaseModel):
        bbox: BBox

    expr = jsonpath_ng.parse('$.properties.bbox')

    matches = expr.find(TestModel.model_json_schema())

    assert len(matches) == 1
    assert matches[0].value == {
        'title': 'Bbox',
        'type': 'array',
        'minItems': 4,
        'items': {
            'type': 'number',
        }
    }
