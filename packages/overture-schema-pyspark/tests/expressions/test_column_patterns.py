"""Tests for column_patterns -- structural PySpark composition helpers.

Each helper composition is exercised as a `_Case`: a uniquely-named input
column, the check built over it, and a predicate on the collected result. The
`results` fixture packs every case's input into one wide single-row DataFrame,
applies every check in one `select`, and collects once -- so the whole file
pays for a single `createDataFrame` + `collect` instead of one pair per test
(the same batch-once pattern the generated conformance harness uses). Cases
needing both a violating and a clean input carry two entries (`*_invalid` /
`*_valid`).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from overture.schema.pyspark.expressions.column_patterns import (
    array_check,
    check_struct_unique,
    coalesce_errors,
    error_msg,
    map_keys_check,
    map_values_check,
    nested_array_check,
    nested_map_keys_check,
    nested_map_values_check,
)
from overture.schema.pyspark.expressions.constraint_expressions import (
    check_bounds,
    check_require_any_of,
    check_string_min_length,
)
from pyspark.sql import Column, SparkSession
from pyspark.sql import functions as F

# PySpark 3.4's collect() leaves its result socket for the GC to finalize; under
# -W error that ResourceWarning fails the batched `results` fixture. conftest's
# unraisablehook catches the finalizer path, but this fixture emits it
# synchronously -- and a filterwarnings mark is the only filter outranking the
# command-line -W error.
pytestmark = pytest.mark.filterwarnings("ignore::ResourceWarning")


@dataclass(frozen=True)
class _Case:
    """One column_patterns assertion driven off the shared wide row.

    `check(field)` builds the composition over the case's input column;
    `expect(result)` is a predicate on that column's single collected value.
    """

    id: str
    ddl: str
    value: Any
    check: Callable[[str], Column]
    expect: Callable[[Any], bool]


_CASES: list[_Case] = [
    # --- error_msg: builds a string message, not an error array ---------------
    _Case(
        "em_concat",
        "string",
        "bad",
        lambda f: error_msg("field: got ", F.col(f)),
        lambda r: r == "field: got bad",
    ),
    _Case(
        "em_multi",
        "struct<a:string,b:string>",
        {"a": "x", "b": "y"},
        lambda f: error_msg("prefix ", F.col(f)["a"], F.lit(" and "), F.col(f)["b"]),
        lambda r: r == "prefix x and y",
    ),
    # A NULL interpolated value must not nullify the whole message (F.concat
    # would): a NULL message is dropped by array_compact, silently swallowing the
    # violation (e.g. an out-of-bounds range [null, 1.5]). It renders literally.
    _Case(
        "em_null",
        "double",
        None,
        lambda f: error_msg("got ", F.col(f)),
        lambda r: r == "got null",
    ),
    # --- array_check ----------------------------------------------------------
    _Case(
        "ac_null",
        "array<struct<val:string>>",
        None,
        lambda f: array_check(f, lambda el: F.lit("err")),
        lambda r: r is None,
    ),
    _Case(
        "ac_filter",
        "array<struct<val:string>>",
        [{"val": "ok"}, {"val": "bad"}],
        lambda f: array_check(f, lambda el: F.when(el["val"] == "bad", F.lit("error"))),
        lambda r: r == ["error"],
    ),
    _Case(
        "ac_empty",
        "array<struct<val:string>>",
        [{"val": "ok"}],
        lambda f: array_check(f, lambda el: F.when(el["val"] == "bad", F.lit("error"))),
        lambda r: r == [],
    ),
    # array_check / check_struct_unique also accept a Column, not just a name.
    _Case(
        "ac_col",
        "array<struct<val:string>>",
        [{"val": "ok"}, {"val": "bad"}],
        lambda f: array_check(
            F.col(f), lambda el: F.when(el["val"] == "bad", F.lit("error"))
        ),
        lambda r: r == ["error"],
    ),
    # --- check_struct_unique --------------------------------------------------
    _Case(
        "su_nodup",
        "array<struct<id:string>>",
        [{"id": "a"}, {"id": "b"}],
        lambda f: check_struct_unique(f),
        lambda r: r is None,
    ),
    _Case(
        "su_dup",
        "array<struct<id:string>>",
        [{"id": "a"}, {"id": "a"}],
        lambda f: check_struct_unique(f),
        lambda r: r is not None and "duplicate" in r,
    ),
    _Case(
        "su_null",
        "array<struct<id:string>>",
        None,
        lambda f: check_struct_unique(f),
        lambda r: r is None,
    ),
    # Same value subfield but different other fields is not a duplicate.
    _Case(
        "su_repeat",
        "array<struct<value:string,pos:double>>",
        [
            {"value": "a", "pos": 0.0},
            {"value": "b", "pos": 0.5},
            {"value": "a", "pos": 0.7},
        ],
        lambda f: check_struct_unique(f),
        lambda r: r is None,
    ),
    _Case(
        "su_single",
        "array<struct<id:string>>",
        [{"id": "a"}],
        lambda f: check_struct_unique(f),
        lambda r: r is None,
    ),
    _Case(
        "csu_col",
        "array<struct<id:string>>",
        [{"id": "a"}, {"id": "a"}],
        lambda f: check_struct_unique(F.col(f)),
        lambda r: r is not None and "duplicate" in r,
    ),
    _Case(
        "csu_colnull",
        "array<struct<id:string>>",
        None,
        lambda f: check_struct_unique(F.col(f)),
        lambda r: r is None,
    ),
    # --- nested_array_check ---------------------------------------------------
    _Case(
        "na_flat",
        "array<struct<tags:array<string>>>",
        [{"tags": ["good", "bad"]}, {"tags": ["worse"]}],
        lambda f: coalesce_errors(
            nested_array_check(
                f,
                lambda el: array_check(
                    el["tags"],
                    lambda tag: F.when(tag != "good", F.concat(F.lit("bad: "), tag)),
                ),
            )
        ),
        lambda r: len(r) == 2 and all(isinstance(e, str) for e in r),
    ),
    _Case(
        "na_null",
        "array<struct<tags:array<string>>>",
        None,
        lambda f: coalesce_errors(
            nested_array_check(
                f,
                lambda el: array_check(
                    el["tags"], lambda tag: F.when(tag != "good", F.lit("bad"))
                ),
            )
        ),
        lambda r: r == [],
    ),
    # A null inner array must not nullify sibling errors during flatten:
    # F.flatten returns NULL whenever any sub-array is NULL, which would drop
    # every sibling error unless inner nulls are guarded.
    _Case(
        "na_mixed",
        "array<struct<tags:array<string>>>",
        [{"tags": ["good"]}, {"tags": None}, {"tags": ["bad"]}],
        lambda f: coalesce_errors(
            nested_array_check(
                f,
                lambda el: array_check(
                    el["tags"],
                    lambda tag: F.when(tag != "good", F.concat(F.lit("bad: "), tag)),
                ),
            )
        ),
        lambda r: r == ["bad: bad"],
    ),
    _Case(
        "na_noerr",
        "array<struct<tags:array<string>>>",
        [{"tags": ["good"]}],
        lambda f: coalesce_errors(
            nested_array_check(
                f,
                lambda el: array_check(
                    el["tags"], lambda tag: F.when(tag != "good", F.lit("bad"))
                ),
            )
        ),
        lambda r: r == [],
    ),
    # --- map_keys_check / map_values_check ------------------------------------
    _Case(
        "mk_bad",
        "map<string,string>",
        {"good": "v", "bad": "v"},
        lambda f: map_keys_check(f, lambda k: F.when(k == "bad", F.lit("bad key"))),
        lambda r: r == ["bad key"],
    ),
    _Case(
        "mv_bad",
        "map<string,string>",
        {"a": "ok", "b": "bad"},
        lambda f: map_values_check(f, lambda v: F.when(v == "bad", F.lit("bad value"))),
        lambda r: r == ["bad value"],
    ),
    # A field check on a dict[str, Model] value navigates into the value struct
    # -- the exact composition the renderer emits for a map-of-model value field.
    _Case(
        "mv_struct",
        "map<string,struct<label:string>>",
        {"a": {"label": ""}},
        lambda f: map_values_check(f, lambda v: check_string_min_length(v["label"], 1)),
        lambda r: r == ["minimum length 1, got 0"],
    ),
    _Case(
        "mv_struct_ok",
        "map<string,struct<label:string>>",
        {"a": {"label": "ok"}},
        lambda f: map_values_check(f, lambda v: check_string_min_length(v["label"], 1)),
        lambda r: r == [],
    ),
    # A model-level constraint on a dict[str, Model] value -- the composition the
    # renderer emits for a map-of-model value-model constraint.
    _Case(
        "mv_model",
        "map<string,struct<foo:int,bar:string>>",
        {"a": {"foo": None, "bar": None}},
        lambda f: map_values_check(
            f, lambda v: check_require_any_of([v["foo"], v["bar"]], ["foo", "bar"])
        ),
        lambda r: r == ["requires at least one of foo, bar"],
    ),
    _Case(
        "mv_model_ok",
        "map<string,struct<foo:int,bar:string>>",
        {"a": {"foo": 1, "bar": None}},
        lambda f: map_values_check(
            f, lambda v: check_require_any_of([v["foo"], v["bar"]], ["foo", "bar"])
        ),
        lambda r: r == [],
    ),
    _Case(
        "mk_null",
        "map<string,string>",
        None,
        lambda f: map_keys_check(f, lambda k: F.lit("err")),
        lambda r: r is None,
    ),
    _Case(
        "mv_valid",
        "map<string,string>",
        {"a": "ok"},
        lambda f: map_values_check(f, lambda v: F.when(v == "bad", F.lit("err"))),
        lambda r: r == [],
    ),
    _Case(
        "mk_col",
        "map<string,string>",
        {"bad": "v"},
        lambda f: map_keys_check(F.col(f), lambda k: F.when(k == "bad", F.lit("err"))),
        lambda r: r == ["err"],
    ),
    # --- coalesce_errors (input-independent literals) -------------------------
    _Case(
        "coal_null",
        "int",
        1,
        lambda f: coalesce_errors(F.lit(None).cast("array<string>")),
        lambda r: r == [],
    ),
    _Case(
        "coal_array",
        "int",
        1,
        lambda f: coalesce_errors(F.array(F.lit("err"))),
        lambda r: r == ["err"],
    ),
    # --- nested_map_{values,keys}_check flatten an inner array<string> --------
    _Case(
        "nmv_flat_invalid",
        "map<string,array<int>>",
        {"a": [1, 0], "b": [2]},
        lambda f: nested_map_values_check(
            f,
            lambda v: array_check(
                v, lambda e: F.when(e == 0, F.lit("zero not allowed"))
            ),
        ),
        lambda r: r == ["zero not allowed"],
    ),
    _Case(
        "nmv_flat_valid",
        "map<string,array<int>>",
        {"a": [1], "b": [3]},
        lambda f: nested_map_values_check(
            f,
            lambda v: array_check(
                v, lambda e: F.when(e == 0, F.lit("zero not allowed"))
            ),
        ),
        lambda r: r == [],
    ),
    _Case(
        "nmk_flat_invalid",
        "map<string,int>",
        {"ax": 1, "b": 2},
        lambda f: nested_map_keys_check(
            f,
            lambda k: array_check(
                F.split(k, ""), lambda ch: F.when(ch == "x", F.lit("x not allowed"))
            ),
        ),
        lambda r: r == ["x not allowed"],
    ),
    _Case(
        "nmk_flat_valid",
        "map<string,int>",
        {"cd": 1},
        lambda f: nested_map_keys_check(
            f,
            lambda k: array_check(
                F.split(k, ""), lambda ch: F.when(ch == "x", F.lit("x not allowed"))
            ),
        ),
        lambda r: r == [],
    ),
    # --- flattening helper wrapped around map_values_check --------------------
    # `items[].tags{value}` and `subs{value}{value}`: the pairings the generated
    # nested_array_check / nested_map_values_check fold around map_values_check.
    _Case(
        "nawmv_invalid",
        "array<struct<tags:map<string,string>>>",
        [{"tags": {"k": "ab"}}],
        lambda f: nested_array_check(
            f,
            lambda el: map_values_check(
                el["tags"], lambda v: check_string_min_length(v, 3)
            ),
        ),
        lambda r: r != [],
    ),
    _Case(
        "nawmv_valid",
        "array<struct<tags:map<string,string>>>",
        [{"tags": {"k": "abc"}}, {"tags": {"k2": "wxyz"}}],
        lambda f: nested_array_check(
            f,
            lambda el: map_values_check(
                el["tags"], lambda v: check_string_min_length(v, 3)
            ),
        ),
        lambda r: r == [],
    ),
    _Case(
        "nmvwmv_invalid",
        "map<string,map<string,int>>",
        {"k": {"a": -2}},
        lambda f: nested_map_values_check(
            f,
            lambda v: map_values_check(
                v, lambda w: check_bounds(w, ge=0, check_nan=False)
            ),
        ),
        lambda r: r != [],
    ),
    _Case(
        "nmvwmv_valid",
        "map<string,map<string,int>>",
        {"k": {"a": 0, "b": 1}},
        lambda f: nested_map_values_check(
            f,
            lambda v: map_values_check(
                v, lambda w: check_bounds(w, ge=0, check_nan=False)
            ),
        ),
        lambda r: r == [],
    ),
]


@pytest.fixture(scope="module")
def results(spark: SparkSession) -> Any:
    """Pack every case's input into one row, apply every check, collect once."""
    # A DDL schema string, not StructType.fromDDL -- fromDDL landed in PySpark
    # 3.5, and createDataFrame parses the string itself on the >=3.4 floor.
    schema = ", ".join(f"`{c.id}` {c.ddl}" for c in _CASES)
    row = {c.id: c.value for c in _CASES}
    # dict rows are read by field name against the explicit schema, a form the
    # createDataFrame stubs don't model (they want tuple/Row for RowLike).
    df = spark.createDataFrame([row], schema=schema, verifySchema=False)  # type: ignore[call-overload]
    return df.select(*[c.check(c.id).alias(c.id) for c in _CASES]).collect()[0]


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.id)
def test_column_pattern(case: _Case, results: Any) -> None:
    value = results[case.id]
    assert case.expect(value), f"{case.id}: got {value!r}"
