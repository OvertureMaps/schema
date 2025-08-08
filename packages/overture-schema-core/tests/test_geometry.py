import re
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import chain, combinations
from typing import Annotated, Any

import pytest
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint
from pydantic import BaseModel, ValidationError
from pytest_subtests import SubTests


def test_geometry_type_sorted() -> None:
    enumerated_order = tuple(GeometryType)

    assert enumerated_order == tuple(sorted(enumerated_order))

    indices = [item._value for item in enumerated_order]

    assert indices == list(range(0, len(indices)))


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


TEST_GEOMETRY_TYPE_CASES: tuple[GeometryTypeCase] = (
    GeometryTypeCase(
        geometry_type=GeometryType.POINT,
        examples=(
            {"type": "Point", "coordinates": [0, 0]},
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
def test_geometry_type_constraint_valid(
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
            for counterexample in geometry_type_case.counterexamples:
                with subtests.test(counterexample=counterexample):
                    with pytest.raises(ValidationError):
                        ConstrainedModel(geometry=counterexample)
