"""Tests for Check dataclass and CheckShape enum."""

import dataclasses

import pytest
from overture.schema.pyspark.check import Check, CheckShape
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def test_check_is_frozen(spark: SparkSession) -> None:
    check = Check(
        field="subtype",
        name="required",
        expr=F.lit("error"),
        shape=CheckShape.SCALAR,
        read_columns=frozenset({"subtype"}),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        check.field = "other"  # type: ignore[misc]
