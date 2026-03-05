"""Shared per-CheckType test cases: models, expected rules, sample data, expected violations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal

from overture.schema.system.field_constraint import (
    PatternConstraint,
    UniqueItemsConstraint,
)
from overture.schema.system.model_constraint import (
    forbid_if,
    radio_group,
    require_any_of,
)
from overture.schema.system.model_constraint.model_constraint import FieldEqCondition
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.validation.ir import (
    CheckType,
    Condition,
    DatasetSpec,
    Rule,
    Severity,
)
from pydantic import BaseModel, Field


class BaseId(BaseModel):
    id: str


@dataclass
class CheckTypeCase:
    """A single per-CheckType test case."""

    model: type[BaseModel]
    rules: list[Rule]
    create_sql: str
    violations: dict[str, list[str]]
    extra_rules: list[Rule] = field(default_factory=list)

    @property
    def expected_spec(self) -> DatasetSpec:
        _ID = Rule(
            name="test.id.not_null",
            column="id",
            check=CheckType.NOT_NULL,
            severity=Severity.ERROR,
        )
        return DatasetSpec(
            name="test",
            source_model=f"{self.model.__module__}.{self.model.__qualname__}",
            id_column="id",
            rules=[_ID] + self.extra_rules + self.rules,
        )


# ---------------------------------------------------------------------------
# Models (one per CheckType)
# ---------------------------------------------------------------------------


class NotNullModel(BaseId):
    col: str


class GtModel(BaseId):
    col: int | None = Field(gt=4)


class GteModel(BaseId):
    col: int | None = Field(ge=5)


class LtModel(BaseId):
    col: float | None = Field(lt=10.0)


class LteModel(BaseId):
    col: int | None = Field(le=10)


class EqModel(BaseId):
    col: Literal["x"] | None = None


class BetweenModel(BaseId):
    col: int | None = Field(ge=0, le=100)


class InModel(BaseId):
    col: Literal["a", "b", "c"] | None = None


class MinLengthModel(BaseId):
    col: str | None = Field(min_length=3)


class MaxLengthModel(BaseId):
    col: str | None = Field(max_length=5)


class IsTypeModel(BaseId):
    col: Annotated[bool | None, Field(strict=True)] = None


class UniqueModel(BaseId):
    col: Annotated[list[str] | None, UniqueItemsConstraint()] = None


class PatternModel(BaseId):
    col: Annotated[str | None, PatternConstraint(r"^[A-Z]{2}$", "msg")] = None


class GeometryTypeModel(BaseId):
    geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.POINT)]


@forbid_if(["col"], FieldEqCondition("flag", "x"))
class IsNullModel(BaseId):
    flag: str
    col: str | None = None


@radio_group("a", "b")
class ExactlyOneOfModel(BaseId):
    a: bool | None = None
    b: bool | None = None


@require_any_of("a", "b")
class AnyOfModel(BaseId):
    a: str | None = None
    b: str | None = None


# ---------------------------------------------------------------------------
# Cases dict
# ---------------------------------------------------------------------------


CASES: dict[str, CheckTypeCase] = {
    "not_null": CheckTypeCase(
        model=NotNullModel,
        rules=[
            Rule(
                name="test.col.not_null",
                column="col",
                check=CheckType.NOT_NULL,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'x'), ('b', NULL), ('c', 'y')
            ) AS t(id, col)
        """,
        violations={"test.col.not_null": ["b"]},
    ),
    "gt": CheckTypeCase(
        model=GtModel,
        rules=[
            Rule(
                name="test.col.gt",
                column="col",
                check=CheckType.GT,
                value=4,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 5), ('b', 3), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.gt": ["b"]},
    ),
    "gte": CheckTypeCase(
        model=GteModel,
        rules=[
            Rule(
                name="test.col.gte",
                column="col",
                check=CheckType.GTE,
                value=5,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 5), ('b', 4), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.gte": ["b"]},
    ),
    "lt": CheckTypeCase(
        model=LtModel,
        rules=[
            Rule(
                name="test.col.lt",
                column="col",
                check=CheckType.LT,
                value=10.0,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 5.0), ('b', 15.0), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.lt": ["b"]},
    ),
    "lte": CheckTypeCase(
        model=LteModel,
        rules=[
            Rule(
                name="test.col.lte",
                column="col",
                check=CheckType.LTE,
                value=10,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 10), ('b', 11), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.lte": ["b"]},
    ),
    "eq": CheckTypeCase(
        model=EqModel,
        rules=[
            Rule(
                name="test.col.eq",
                column="col",
                check=CheckType.EQ,
                value="x",
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'x'), ('b', 'y'), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.eq": ["b"]},
    ),
    "between": CheckTypeCase(
        model=BetweenModel,
        rules=[
            Rule(
                name="test.col.range",
                column="col",
                check=CheckType.BETWEEN,
                value=[0, 100],
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 50), ('b', 101), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.range": ["b"]},
    ),
    "in": CheckTypeCase(
        model=InModel,
        rules=[
            Rule(
                name="test.col.valid",
                column="col",
                check=CheckType.IN,
                value=["a", "b", "c"],
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'b'), ('b', 'z'), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.valid": ["b"]},
    ),
    "min_length": CheckTypeCase(
        model=MinLengthModel,
        rules=[
            Rule(
                name="test.col.min_length",
                column="col",
                check=CheckType.MIN_LENGTH,
                value=3,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'abc'), ('b', 'ab'), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.min_length": ["b"]},
    ),
    "max_length": CheckTypeCase(
        model=MaxLengthModel,
        rules=[
            Rule(
                name="test.col.max_length",
                column="col",
                check=CheckType.MAX_LENGTH,
                value=5,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'abc'), ('b', 'abcdef'), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.max_length": ["b"]},
    ),
    "is_type": CheckTypeCase(
        model=IsTypeModel,
        rules=[
            Rule(
                name="test.col.type",
                column="col",
                check=CheckType.IS_TYPE,
                value="boolean",
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 1), ('b', 0), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.type": ["a", "b"]},
    ),
    "unique": CheckTypeCase(
        model=UniqueModel,
        rules=[
            Rule(
                name="test.col.unique",
                column="col",
                check=CheckType.UNIQUE,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS
            SELECT 'a' AS id, ['x', 'y'] AS col
            UNION ALL SELECT 'b', ['x', 'x']
            UNION ALL SELECT 'c', NULL
        """,
        violations={"test.col.unique": ["b"]},
    ),
    "pattern": CheckTypeCase(
        model=PatternModel,
        rules=[
            Rule(
                name="test.col.pattern",
                column="col",
                check=CheckType.PATTERN,
                value=r"^[A-Z]{2}$",
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'US'), ('b', 'usa'), ('c', NULL)
            ) AS t(id, col)
        """,
        violations={"test.col.pattern": ["b"]},
    ),
    "geometry_type": CheckTypeCase(
        model=GeometryTypeModel,
        extra_rules=[
            Rule(
                name="test.geometry.not_null",
                column="geometry",
                check=CheckType.NOT_NULL,
                severity=Severity.ERROR,
            ),
        ],
        rules=[
            Rule(
                name="test.geometry.type",
                column="geometry",
                check=CheckType.GEOMETRY_TYPE,
                value=["Point"],
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            INSTALL spatial;
            LOAD spatial;
            CREATE TABLE _tbl AS
            SELECT 'a' AS id, ST_AsWKB(ST_Point(0, 0))::BLOB AS geometry
            UNION ALL SELECT 'b', ST_AsWKB(ST_GeomFromText('POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))'))::BLOB
            UNION ALL SELECT 'c', ST_AsWKB(ST_Point(1, 1))::BLOB
        """,
        violations={"test.geometry.type": ["b"]},
    ),
    "is_null": CheckTypeCase(
        model=IsNullModel,
        extra_rules=[
            Rule(
                name="test.flag.not_null",
                column="flag",
                check=CheckType.NOT_NULL,
                severity=Severity.ERROR,
            ),
        ],
        rules=[
            Rule(
                name="test.col.forbidden_when",
                column="col",
                check=CheckType.IS_NULL,
                when=Condition(column="flag", check=CheckType.EQ, value="x"),
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'x', NULL), ('b', 'x', 'val'), ('c', 'y', 'val')
            ) AS t(id, flag, col)
        """,
        violations={"test.col.forbidden_when": ["b"]},
    ),
    "exactly_one_of": CheckTypeCase(
        model=ExactlyOneOfModel,
        rules=[
            Rule(
                name="test.a_b.exactly_one_of",
                columns=["a", "b"],
                check=CheckType.EXACTLY_ONE_OF,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS
            SELECT 'a' AS id, true AS a, CAST(NULL AS BOOLEAN) AS b
            UNION ALL SELECT 'b', true, true
            UNION ALL SELECT 'c', CAST(NULL AS BOOLEAN), true
        """,
        violations={"test.a_b.exactly_one_of": ["b"]},
    ),
    "any_of": CheckTypeCase(
        model=AnyOfModel,
        rules=[
            Rule(
                name="test.a_b.any_of",
                columns=["a", "b"],
                check=CheckType.ANY_OF,
                severity=Severity.ERROR,
            ),
        ],
        create_sql="""
            CREATE TABLE _tbl AS SELECT * FROM (VALUES
                ('a', 'x', NULL), ('b', NULL, NULL), ('c', NULL, 'y')
            ) AS t(id, a, b)
        """,
        violations={"test.a_b.any_of": ["b"]},
    ),
}
