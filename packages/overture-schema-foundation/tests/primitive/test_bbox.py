from typing import Any

import jsonpath_ng  # type: ignore[import-untyped]
import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.foundation.primitive.bbox import BBox


@pytest.mark.parametrize(
    "xmin, ymin, xmax, ymax",
    [
        ("foo", 2, 3, 4),
        (1, "foo", 3, 4),
        (1, 2, "foo", 4),
        (1, 2, 3, "foo"),
    ],
)
def test_bbox_construct_invalid_type(
    xmin: Any, ymin: Any, xmax: Any, ymax: Any
) -> None:
    with pytest.raises(TypeError):
        BBox(xmin, ymin, xmax, ymax)


def test_bbox_construct_positional() -> None:
    bbox = BBox(1, 2, 3, 4.0)

    assert bbox.xmin == 1
    assert bbox.ymin == 2
    assert bbox.xmax == 3
    assert bbox.ymax == 4.0


def test_bbox_construct_keyword() -> None:
    bbox = BBox(xmin=1.0, ymin=2.0, xmax=3.0, ymax=4)

    assert bbox.xmin == 1.0
    assert bbox.ymin == 2.0
    assert bbox.xmax == 3.0
    assert bbox.ymax == 4


def test_bbox_immutable() -> None:
    bbox = BBox(1, 2, 3, 4)

    with pytest.raises(AttributeError):
        bbox.xmin = -1  # type: ignore[misc]

    with pytest.raises(AttributeError):
        bbox.ymin = -2  # type: ignore[misc]

    with pytest.raises(AttributeError):
        bbox.xmax = -3  # type: ignore[misc]

    with pytest.raises(AttributeError):
        bbox.ymax = -4  # type: ignore[misc]

    assert bbox == BBox(1, 2, 3, 4)


@pytest.mark.parametrize(
    "a, b",
    [
        (BBox(0, 0, 0, 0), BBox(0, 0, 0, 0)),
        (BBox(0, 0, 0, 0), BBox(0.0, 0.0, 0.0, 0.0)),
        (BBox(1, 2, 3, 4), BBox(1.0, 2.0, 3.0, 4.0)),
        (BBox(-1.0, 0.5, 1.5, 2.5), BBox(-1, 0.5, 1.5, 2.5)),
    ],
)
def test_bbox_eq(a: BBox, b: BBox) -> None:
    assert a == a
    assert b == b
    assert a == b
    assert b == a
    assert hash(a) == hash(a)
    assert hash(a) == hash(b)

    c = BBox(a.xmin + 1, a.ymin, a.xmax, a.ymax)
    assert c == c
    assert a != c
    assert c != a

    d = BBox(a.xmin, a.ymin + 1, a.xmax, a.ymax)
    assert d == d
    assert a != d
    assert d != a

    e = BBox(a.xmin, a.ymin, a.xmax + 1, a.ymax)
    assert e == e
    assert a != e
    assert e != a

    f = BBox(a.xmin, a.ymin, a.xmax, a.ymax + 1)
    assert f == f
    assert a != f
    assert f != a


def test_bbox_repr() -> None:
    bbox = BBox(1, 2, 3.5, 4)

    assert repr(bbox) == "BBox(1, 2, 3.5, 4)"


def test_bbox_str() -> None:
    bbox = BBox(-1.25, 2.0, -3, 4.75)

    assert str(bbox) == "(-1.25, 2.0, -3, 4.75)"


def test_bbox_to_geo_json() -> None:
    bbox = BBox(-10, -20, 30, 40)

    assert bbox.to_geo_json() == (-10, -20, 30, 40)


@pytest.mark.parametrize(
    "geo_json, expect",
    [
        [(1, 2, 3, 4), BBox(1, 2, 3, 4)],
        [[-1.0, -2.0, 1.0, 2.0], BBox(-1.0, -2.0, 1.0, 2.0)],
    ],
)
def test_bbox_from_geo_json_success(
    geo_json: tuple[float | int, ...], expect: BBox
) -> None:
    # Test the sequence form where you pass in a tuple/list.
    actual = BBox.from_geo_json(geo_json)
    assert actual == expect

    # Test the vararg form.
    actual = BBox.from_geo_json(*geo_json)
    assert actual == expect


@pytest.mark.parametrize(
    "bad_input",
    [
        ({}, 2, 3, 4),
        [1, 2, 3, "foo"],
    ],
)
def test_bbox_from_geo_json_type_error(bad_input: Any) -> None:
    # Test the sequence form where you pass in a tuple/list.
    with pytest.raises(TypeError):
        BBox.from_geo_json(bad_input)

    # Test the vararg form.
    with pytest.raises(TypeError):
        BBox.from_geo_json(*bad_input)


@pytest.mark.parametrize(
    "bad_input",
    [
        (()),
        ((1,)),
        ((1, 2)),
        ((1, 2, 3)),
        ((1, 2, 3, 4, 5)),
        ([]),
        (["foo"]),
        (["foo", "bar"]),
        (["foo", "bar", "baz"]),
        (["foo", "bar", "baz", "qux", "corge"]),
    ],
)
def test_bbox_from_geo_json_value_error(bad_input: tuple[float | int, ...]) -> None:
    # Test the sequence form where you pass in a tuple/list.
    with pytest.raises(ValueError):
        BBox.from_geo_json(bad_input)

    # Test the vararg form.
    with pytest.raises(ValueError):
        BBox.from_geo_json(*bad_input)


def test_pydantic_json() -> None:
    class TestModel(BaseModel):
        bbox: BBox

    bbox = BBox(1, 2, 3, 4)
    test_model = TestModel(bbox=bbox)

    expect = {
        "bbox": [1, 2, 3, 4],
    }

    assert test_model.model_dump(mode="json") == expect


@pytest.mark.parametrize(
    "input, expect",
    [
        ((1, 2, 3, 4), BBox(xmin=1, ymin=2, xmax=3, ymax=4)),
        (BBox(0, -1, -2, 3), BBox(0, -1, -2, 3)),
    ],
)
def test_pydantic_validation_success(input: Any, expect: BBox) -> None:
    class TestModel(BaseModel):
        bbox: BBox

    test_model = TestModel(bbox=input)

    assert test_model.bbox == expect


@pytest.mark.parametrize(
    "input",
    [
        "foo",
    ],
)
def test_pydantic_validation_error(input: Any) -> None:
    class TestModel(BaseModel):
        bbox: BBox

    with pytest.raises(ValidationError):
        TestModel(bbox=input)


def test_pydantic_json_schema() -> None:
    class TestModel(BaseModel):
        bbox: BBox

    expr = jsonpath_ng.parse("$.properties.bbox")

    matches = expr.find(TestModel.model_json_schema())

    assert len(matches) == 1
    assert matches[0].value == {
        "title": "Bbox",
        "type": "array",
        "minItems": 4,
        "maxItems": 4,
        "items": {
            "type": "number",
        },
    }
