import re
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import chain, combinations
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, ValidationError
from pytest_subtests import SubTests
from shapely import wkt

from overture.schema.foundation.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


def test_geometry_type_sorted() -> None:
    enumerated_order = tuple(GeometryType)

    assert enumerated_order == tuple(sorted(enumerated_order))


def test_geometry_type_geo_json_type() -> None:
    def to_upper_camel_case(s: str) -> str:
        parts = re.split(r"[^a-zA-Z0-9]", s)
        return "".join(word.capitalize() for word in parts if word)

    actual = [item.geo_json_type for item in GeometryType]
    expected = [to_upper_camel_case(item.name) for item in GeometryType]

    assert actual == expected


def test_geometry_type_constraint_empty() -> None:
    with pytest.raises(ValueError):

        class EmptyGeometryTypeConstraintModel(BaseModel):
            geometry: Annotated[Geometry, GeometryTypeConstraint()]


def test_geometry_type_constraint_invalid() -> None:
    with pytest.raises(ValueError):

        class InvalidGeometryTypeConstraintModel(BaseModel):
            geometry: Annotated[Geometry, GeometryTypeConstraint("foo")]


@dataclass
class GeometryTypeCase:
    geometry_type: GeometryType
    examples: tuple[dict[Any, Any], ...] = ()
    counterexamples: tuple[dict[Any, Any], ...] = ()


TEST_GEOMETRY_TYPE_CASES: tuple[GeometryTypeCase, ...] = (
    GeometryTypeCase(
        geometry_type=GeometryType.GEOMETRY_COLLECTION,
        examples=(
            {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "LineString", "coordinates": [[0, 0], [-1, -1]]}
                ],
            },
            {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]]]}
                ],
            },
            {
                "type": "GeometryCollection",
                "geometries": [{"type": "MultiPoint", "coordinates": [[0, 0], [1, 1]]}],
            },
            {
                "type": "GeometryCollection",
                "geometries": [
                    {
                        "type": "MultiPolygon",
                        "coordinates": [[[[0, 0], [-1, 0], [-1, -1], [0, 0]]]],
                    }
                ],
            },
            {
                "type": "GeometryCollection",
                "geometries": [{"type": "Point", "coordinates": [0, 0]}],
            },
            {
                "type": "GeometryCollection",
                "geometries": [
                    {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [-1, 0], [-1, -1], [0, 0]]],
                    }
                ],
            },
            {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "LineString", "coordinates": [[0, 0], [-1, -1]]},
                    {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]]]},
                    {"type": "MultiPoint", "coordinates": [[0, 0], [1, 1]]},
                    {
                        "type": "MultiPolygon",
                        "coordinates": [[[[0, 0], [-1, 0], [-1, -1], [0, 0]]]],
                    },
                    {"type": "Point", "coordinates": [0, 0]},
                    {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [-1, 0], [-1, -1], [0, 0]]],
                    },
                ],
            },
        ),
        counterexamples=(
            {"type": "GeometryCollection", "geometry": []},
            {"type": "GeometryCollection", "geometries": []},
            {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "LineString", "coordinates": [[0, 0], [-1, -1]]},
                    {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]]]},
                    {"type": "MultiPoint", "coordinates": [[0, 0], [1, 1]]},
                    {
                        "type": "MultiPolygon",
                        "coordinates": [[[[0, 0], [-1, 0], [-1, -1], [0, 0]]]],
                    },
                    {"type": "Point", "coordinates": [0, 0]},
                    {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [-1, 0], [-1, -1], [0, 0]]],
                    },
                    {"type": "foo", "coordinates": []},
                ],
            },
        ),
    ),
    GeometryTypeCase(
        geometry_type=GeometryType.LINE_STRING,
        examples=(
            {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            {"type": "LineString", "coordinates": [[0, 0], [1, 1], [2, 2]]},
            {"type": "LineString", "coordinates": [[-1.5, 3], [-1.0, 2.0], [0.0, 0]]},
        ),
        counterexamples=(
            {},
            {"type": "LineString"},
            {"coordinates": [[0, 0], [1, 1]]},
            {"type": "LineString", "coordinates": []},
            {"type": "LineString", "coordinates": [0]},
            {"type": "LineString", "coordinates": [0, 0]},
            {"type": "LineString", "coordinates": [[0, 0]]},
        ),
    ),
    GeometryTypeCase(
        geometry_type=GeometryType.MULTI_LINE_STRING,
        examples=(
            {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]]]},
            {
                "type": "MultiLineString",
                "coordinates": [[[0, 0], [1, 1]], [[2, 2], [3, 3], [4, 4]]],
            },
        ),
        counterexamples=(
            {"type": "MultiLineString"},
            {"type": "MultiLineString", "coordinates": []},
            {"type": "MultiLineString", "coordinates": [[]]},
            {"type": "MultiLineString", "coordinates": [0, 0]},
            {"type": "MultiLineString", "coordinates": [[0, 0]]},
            {"type": "MultiLineString", "coordinates": [[[0, 0]]]},
        ),
    ),
    GeometryTypeCase(
        geometry_type=GeometryType.MULTI_POINT,
        examples=(
            {"type": "MultiPoint", "coordinates": [[0, 0]]},
            {"type": "MultiPoint", "coordinates": [[0, 0], [1, 1]]},
            {
                "type": "MultiPoint",
                "coordinates": [[0, 0], [1, 1], [2, 2]],
                "bbox": [0, 0, 2, 2],
            },
        ),
        counterexamples=(
            {"type": "MultiPoint"},
            {"type": "MultiPoint", "coordinates": []},
            {"type": "MultiPoint", "coordinates": [[]]},
            {"type": "MultiPoint", "coordinates": [0, 0]},
        ),
    ),
    GeometryTypeCase(
        geometry_type=GeometryType.MULTI_POLYGON,
        examples=(
            {
                "type": "MultiPolygon",
                "coordinates": [[[[0, 0], [0, 1], [1, 1], [0, 0]]]],
            },
            {
                "type": "MultiPolygon",
                "coordinates": [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]],
            },
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [[-2, -2], [-2, 2], [2, 2], [2, -2], [-2, -2]],
                        [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]],
                    ]
                ],
            },
        ),
        counterexamples=(
            {"type": "MultiPolygon", "coordinates": []},
            {"type": "MultiPolygon", "coordinates": [0, 0]},
            {"type": "MultiPolygon", "coordinates": [[0, 0], [1, 1]]},
            {"type": "MultiPolygon", "coordinates": [[[0, 0], [1, 1]]]},
            {"type": "MultiPolygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        ),
    ),
    GeometryTypeCase(
        geometry_type=GeometryType.POINT,
        examples=(
            {"type": "Point", "coordinates": [0, 0], "bbox": [0, 0, 0, 0]},
            {"type": "Point", "coordinates": [0, 0, 0]},
            {"type": "Point", "coordinates": [-90, 131.5]},
        ),
        counterexamples=(
            {},
            {"type": "Point"},
            {"coordinates": [0, 0]},
            {"type": "Point", "coordinates": "foo"},
            {"type": "Point", "coordinates": [0]},
            {"type": "Point", "coordinates": [[0, 0], [1, 1]]},
        ),
    ),
    GeometryTypeCase(
        geometry_type=GeometryType.POLYGON,
        examples=(
            {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
            },
            {
                "type": "Polygon",
                "coordinates": [
                    [[-2, -2], [-2, 2], [2, 2], [2, -2], [-2, -2]],
                    [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]],
                ],
            },
        ),
        counterexamples=(
            {"type": "Polygon", "coordinates": []},
            {"type": "Polygon", "coordinates": [0, 0]},
            {"type": "Polygon", "coordinates": [[0, 0], [1, 1]]},
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]},
        ),
    ),
)


def powerset(
    iterable: tuple[GeometryTypeCase, ...],
) -> Iterator[tuple[GeometryTypeCase, ...]]:
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


TEST_GEOMETRY_TYPE_CASE_SUBSETS = tuple(
    s for s in powerset(TEST_GEOMETRY_TYPE_CASES) if len(s) > 0
)


@pytest.mark.parametrize("geometry_type_case_subset", TEST_GEOMETRY_TYPE_CASE_SUBSETS)
def test_geometry_type_constraint_on_allowed_geometry(
    geometry_type_case_subset: tuple[GeometryTypeCase, ...], subtests: SubTests
) -> None:
    allowed_types = tuple(g.geometry_type for g in geometry_type_case_subset)

    class ConstrainedModel(BaseModel):
        geometry: Annotated[Geometry, GeometryTypeConstraint(*allowed_types)]

    for geometry_type_case in geometry_type_case_subset:
        with subtests.test(geometry_type=geometry_type_case.geometry_type):
            for example in geometry_type_case.examples:
                with subtests.test(example=example):
                    ConstrainedModel(geometry=example)


@pytest.mark.parametrize("geometry_type_case_subset", TEST_GEOMETRY_TYPE_CASE_SUBSETS)
def test_geometry_type_constraint_on_disallowed_geometry(
    geometry_type_case_subset: tuple[GeometryTypeCase, ...], subtests: SubTests
) -> None:
    allowed_types = tuple(g.geometry_type for g in geometry_type_case_subset)

    class ConstrainedModel(BaseModel):
        geometry: Annotated[Geometry, GeometryTypeConstraint(*allowed_types)]

    # Find the geometry type cases that are not allowed.
    non_allowed_cases = tuple(
        c for c in TEST_GEOMETRY_TYPE_CASES if c not in geometry_type_case_subset
    )

    # For each non-allowed case, test one valid example to verify that it doesn't validate.
    for non_allowed_case in non_allowed_cases:
        non_allowed_example = non_allowed_case.examples[0]
        with subtests.test(non_allowed_example=non_allowed_example):
            with pytest.raises(ValidationError):
                ConstrainedModel(geometry=non_allowed_example)


@pytest.mark.parametrize("geometry_type_case_subset", TEST_GEOMETRY_TYPE_CASE_SUBSETS)
def test_geometry_type_constraint_on_geometry_counterexamples(
    geometry_type_case_subset: tuple[GeometryTypeCase, ...], subtests: SubTests
) -> None:
    allowed_types = tuple(g.geometry_type for g in geometry_type_case_subset)

    class ConstrainedModel(BaseModel):
        geometry: Annotated[Geometry, GeometryTypeConstraint(*allowed_types)]

    for geometry_type_case in geometry_type_case_subset:
        with subtests.test(geometry_type=geometry_type_case.geometry_type):
            for counterexample in geometry_type_case.counterexamples:
                with subtests.test(counterexample=counterexample):
                    with pytest.raises(ValidationError):
                        ConstrainedModel(geometry=counterexample)


def test_geometry_immutable() -> None:
    geom = Geometry.from_wkt("POINT(0 0)")

    with pytest.raises(AttributeError):
        geom.geom = wkt.loads("POINT(1 1)")  # type: ignore[misc]

    assert geom == Geometry.from_wkt("POINT(0 0)")


@pytest.mark.parametrize("geometry_type_case", TEST_GEOMETRY_TYPE_CASES)
def test_geometry_geom_type(geometry_type_case: GeometryTypeCase) -> None:
    geo_json = geometry_type_case.examples[0]

    geom = Geometry.from_geo_json(geo_json)

    assert geom.geom_type == geometry_type_case.geometry_type


@pytest.mark.parametrize(
    "wkt",
    [
        "LINESTRING(0 0, 1 1)",
        "MULTILINESTRING((0 0, 1 1), (2 2, 3 3))",
        "MULTIPOINT((0 0), (1 1))",
        "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), ((2 2, 3 2, 3 3, 2 3, 2 2)))",
        "POINT(1 1)",
        "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
    ],
)
def test_geometry_wkt(wkt: str) -> None:
    a = Geometry.from_wkt(wkt)

    def normalize_whitespace(s: str) -> str:
        s = re.sub(r"\s+\(", "(", s)
        s = re.sub(r",\s+", ",", s)
        return s

    assert normalize_whitespace(a.wkt) == normalize_whitespace(wkt)

    b = Geometry.from_wkt(a.wkt)

    assert a == b


def test_geometry_from_wkb() -> None:
    expect = Geometry.from_wkt("POINT(0 0)")
    wkb = b"\x01\x01\x00\x00\x00" + b"\x00" * 16

    actual = Geometry.from_wkb(wkb)

    assert actual == expect
