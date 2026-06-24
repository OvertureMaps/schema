"""Tests for schema comparison."""

from overture.schema.pyspark.schema_check import (
    SchemaMismatch,
    compare_schemas,
)
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    MapType,
    StringType,
    StructField,
    StructType,
)


class TestIdenticalSchemas:
    def test_empty_schemas(self) -> None:
        assert compare_schemas(StructType(), StructType()) == []

    def test_flat_schema(self) -> None:
        schema = StructType(
            [
                StructField("id", StringType(), True),
                StructField("version", IntegerType(), True),
            ]
        )
        assert compare_schemas(schema, schema) == []

    def test_nested_struct(self) -> None:
        schema = StructType(
            [
                StructField(
                    "bbox",
                    StructType(
                        [
                            StructField("xmin", DoubleType(), True),
                        ]
                    ),
                    True,
                ),
            ]
        )
        assert compare_schemas(schema, schema) == []

    def test_array_of_structs(self) -> None:
        schema = StructType(
            [
                StructField(
                    "items",
                    ArrayType(
                        StructType(
                            [
                                StructField("name", StringType(), True),
                            ]
                        )
                    ),
                    True,
                ),
            ]
        )
        assert compare_schemas(schema, schema) == []


class TestMissingFields:
    def test_missing_in_actual(self) -> None:
        actual = StructType([StructField("id", StringType(), True)])
        expected = StructType(
            [
                StructField("id", StringType(), True),
                StructField("version", IntegerType(), True),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("version", "missing", "IntegerType")]

    def test_extra_in_actual(self) -> None:
        actual = StructType(
            [
                StructField("id", StringType(), True),
                StructField("extra", StringType(), True),
            ]
        )
        expected = StructType([StructField("id", StringType(), True)])
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("extra", "StringType", "missing")]


class TestTypeMismatches:
    def test_top_level_type_mismatch(self) -> None:
        actual = StructType([StructField("version", StringType(), True)])
        expected = StructType([StructField("version", IntegerType(), True)])
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("version", "StringType", "IntegerType")]

    def test_nested_struct_mismatch(self) -> None:
        actual = StructType(
            [
                StructField(
                    "bbox",
                    StructType(
                        [
                            StructField("xmin", IntegerType(), True),
                        ]
                    ),
                    True,
                ),
            ]
        )
        expected = StructType(
            [
                StructField(
                    "bbox",
                    StructType(
                        [
                            StructField("xmin", DoubleType(), True),
                        ]
                    ),
                    True,
                ),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("bbox.xmin", "IntegerType", "DoubleType")]

    def test_array_element_type_mismatch(self) -> None:
        actual = StructType(
            [
                StructField("tags", ArrayType(IntegerType()), True),
            ]
        )
        expected = StructType(
            [
                StructField("tags", ArrayType(StringType()), True),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("tags[]", "IntegerType", "StringType")]

    def test_array_struct_field_mismatch(self) -> None:
        actual = StructType(
            [
                StructField(
                    "items",
                    ArrayType(
                        StructType(
                            [
                                StructField("name", IntegerType(), True),
                            ]
                        )
                    ),
                    True,
                ),
            ]
        )
        expected = StructType(
            [
                StructField(
                    "items",
                    ArrayType(
                        StructType(
                            [
                                StructField("name", StringType(), True),
                            ]
                        )
                    ),
                    True,
                ),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("items[].name", "IntegerType", "StringType")]

    def test_map_key_type_mismatch(self) -> None:
        actual = StructType(
            [
                StructField("tags", MapType(IntegerType(), StringType()), True),
            ]
        )
        expected = StructType(
            [
                StructField("tags", MapType(StringType(), StringType()), True),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("tags{key}", "IntegerType", "StringType")]

    def test_map_value_type_mismatch(self) -> None:
        actual = StructType(
            [
                StructField("tags", MapType(StringType(), IntegerType()), True),
            ]
        )
        expected = StructType(
            [
                StructField("tags", MapType(StringType(), StringType()), True),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("tags{value}", "IntegerType", "StringType")]


class TestFieldOrdering:
    def test_different_order_is_ok(self) -> None:
        actual = StructType(
            [
                StructField("b", StringType(), True),
                StructField("a", IntegerType(), True),
            ]
        )
        expected = StructType(
            [
                StructField("a", IntegerType(), True),
                StructField("b", StringType(), True),
            ]
        )
        assert compare_schemas(actual, expected) == []


class TestMultipleMismatches:
    def test_missing_and_extra_and_wrong_type(self) -> None:
        actual = StructType(
            [
                StructField("id", IntegerType(), True),
                StructField("extra", StringType(), True),
            ]
        )
        expected = StructType(
            [
                StructField("id", StringType(), True),
                StructField("version", IntegerType(), True),
            ]
        )
        result = compare_schemas(actual, expected)
        assert SchemaMismatch("id", "IntegerType", "StringType") in result
        assert SchemaMismatch("extra", "StringType", "missing") in result
        assert SchemaMismatch("version", "missing", "IntegerType") in result


class TestKindMismatch:
    def test_struct_vs_primitive(self) -> None:
        actual = StructType([StructField("x", StringType(), True)])
        expected = StructType(
            [
                StructField(
                    "x",
                    StructType(
                        [
                            StructField("y", StringType(), True),
                        ]
                    ),
                    True,
                ),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("x", "StringType", "StructType")]

    def test_array_vs_primitive(self) -> None:
        actual = StructType([StructField("x", StringType(), True)])
        expected = StructType(
            [
                StructField("x", ArrayType(StringType()), True),
            ]
        )
        result = compare_schemas(actual, expected)
        assert result == [SchemaMismatch("x", "StringType", "ArrayType")]


class TestSchemaMismatchRoot:
    """`root` strips the step markers `_compare` embeds in `path`.

    The top-level column a mismatch belongs to is everything before the
    first struct (`.`), array (`[]`), or map (`{key}`/`{value}`) step, so
    it matches the column-granular `Check.read_columns`.
    """

    def test_top_level(self) -> None:
        assert SchemaMismatch("theme", "missing", "StringType").root == "theme"

    def test_struct_field(self) -> None:
        assert SchemaMismatch("bbox.xmin", "missing", "DoubleType").root == "bbox"

    def test_array_element_field(self) -> None:
        assert (
            SchemaMismatch("sources[].confidence", "missing", "DoubleType").root
            == "sources"
        )

    def test_array_element(self) -> None:
        assert SchemaMismatch("tags[]", "IntegerType", "StringType").root == "tags"

    def test_map_key(self) -> None:
        assert SchemaMismatch("tags{key}", "IntegerType", "StringType").root == "tags"

    def test_map_value(self) -> None:
        assert SchemaMismatch("tags{value}", "IntegerType", "StringType").root == "tags"
