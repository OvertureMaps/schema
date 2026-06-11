"""Tests for type registry."""

from overture.schema.codegen.extraction.field import (
    ArrayOf,
    NewTypeShape,
    Primitive,
)
from overture.schema.codegen.extraction.type_registry import (
    PRIMITIVE_TYPES,
    TypeMapping,
    get_type_mapping,
    resolve_type_name,
)


class TestTypeMapping:
    def test_markdown_field(self) -> None:
        assert TypeMapping(markdown="int32").markdown == "int32"

    def test_spark_type_mapping(self) -> None:
        cases = [
            ("str", "StringType()"),
            ("int32", "IntegerType()"),
            ("int64", "LongType()"),
            ("float64", "DoubleType()"),
            ("bool", "BooleanType()"),
            ("Geometry", "BinaryType()"),
            ("float32", "FloatType()"),
        ]
        for type_name, expected in cases:
            mapping = get_type_mapping(type_name)
            assert mapping is not None, f"No mapping for {type_name!r}"
            assert mapping.spark == expected

    def test_bbox_has_no_spark_mapping(self) -> None:
        mapping = get_type_mapping("BBox")
        assert mapping is not None
        assert mapping.spark is None


class TestPrimitiveTypes:
    def test_registry_contains_expected_types(self) -> None:
        expected_types = {
            "int8",
            "int16",
            "int32",
            "int64",
            "uint8",
            "uint16",
            "uint32",
            "float32",
            "float64",
            "str",
            "bool",
            "int",
            "float",
            "Geometry",
            "BBox",
        }
        assert set(PRIMITIVE_TYPES.keys()) == expected_types

    def test_bbox_mapping(self) -> None:
        bbox = PRIMITIVE_TYPES["BBox"]
        assert bbox.markdown == "bbox"
        assert bbox.spark is None


class TestGetTypeMapping:
    def test_returns_mapping_for_known_type(self) -> None:
        assert get_type_mapping("int32").markdown == "int32"  # type: ignore[union-attr]

    def test_returns_none_for_unknown_type(self) -> None:
        assert get_type_mapping("unknown_type") is None

    def test_returns_mapping_for_builtin_int(self) -> None:
        assert get_type_mapping("int").markdown == "int64"  # type: ignore[union-attr]


class TestResolveTypeName:
    def test_unregistered_newtype_falls_back_to_source_type(self) -> None:
        cls = type("SourceItem", (), {})
        shape = NewTypeShape(
            name="Sources",
            ref=object(),
            inner=Primitive(base_type="Sources", source_type=cls),
        )
        assert resolve_type_name(shape) == "SourceItem"

    def test_registered_newtype_resolves_via_registry(self) -> None:
        shape = NewTypeShape(
            name="int32",
            ref=object(),
            inner=Primitive(base_type="int32", source_type=int),
        )
        assert resolve_type_name(shape) == "int32"

    def test_plain_scalar(self) -> None:
        assert (
            resolve_type_name(Primitive(base_type="str", source_type=str)) == "string"
        )

    def test_array_of_scalar_resolves_terminal(self) -> None:
        shape = ArrayOf(element=Primitive(base_type="str", source_type=str))
        assert resolve_type_name(shape) == "string"
