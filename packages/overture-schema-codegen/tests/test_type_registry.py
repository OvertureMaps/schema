"""Tests for type registry."""

import pytest
from overture.schema.codegen.extraction.type_analyzer import TypeInfo, TypeKind
from overture.schema.codegen.extraction.type_registry import (
    PRIMITIVE_TYPES,
    TypeMapping,
    get_type_mapping,
    is_storage_primitive_source,
    resolve_type_name,
)


class TestTypeMapping:
    """Tests for TypeMapping dataclass."""

    def test_typemapping_accepts_markdown(self) -> None:
        """TypeMapping should construct with markdown field."""
        mapping = TypeMapping(markdown="int32")

        assert mapping.markdown == "int32"

    def test_for_target_returns_markdown(self) -> None:
        """for_target should return markdown representation for markdown target."""
        mapping = TypeMapping(markdown="int32")

        assert mapping.for_target("markdown") == "int32"

    def test_for_target_rejects_unknown_target(self) -> None:
        """for_target should raise ValueError for unknown targets."""
        mapping = TypeMapping(markdown="int32")

        with pytest.raises(ValueError, match="Unknown target 'scala'"):
            mapping.for_target("scala")


class TestPrimitiveTypes:
    """Tests for PRIMITIVE_TYPES registry."""

    def test_registry_contains_expected_types(self) -> None:
        """Registry should contain all expected primitive types."""
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
        """BBox should map to bbox."""
        bbox = PRIMITIVE_TYPES["BBox"]

        assert bbox.markdown == "bbox"


class TestGetTypeMapping:
    """Tests for get_type_mapping function."""

    def test_returns_mapping_for_known_type(self) -> None:
        """Should return TypeMapping for known primitive type."""
        result = get_type_mapping("int32")

        assert result is not None
        assert result.markdown == "int32"

    def test_returns_none_for_unknown_type(self) -> None:
        """Should return None for unknown type names."""
        result = get_type_mapping("unknown_type")

        assert result is None

    def test_returns_mapping_for_builtin_int(self) -> None:
        """Should map Python int to int64."""
        result = get_type_mapping("int")

        assert result is not None
        assert result.markdown == "int64"

    def test_returns_mapping_for_builtin_float(self) -> None:
        """Should map Python float to float64."""
        result = get_type_mapping("float")

        assert result is not None
        assert result.markdown == "float64"


class TestResolveTypeNameNewTypeFallback:
    """Tests for resolve_type_name with unregistered NewTypes."""

    def test_unregistered_newtype_falls_back_to_source_type(self) -> None:
        """Unregistered NewType resolves to source_type name."""
        ti = TypeInfo(
            base_type="Sources",
            kind=TypeKind.MODEL,
            newtype_name="Sources",
            source_type=type("SourceItem", (), {}),
        )
        result = resolve_type_name(ti, "markdown")

        assert result == "SourceItem"

    def test_registered_newtype_unaffected(self) -> None:
        """Registered NewType (int32) still resolves through the registry."""
        ti = TypeInfo(
            base_type="int32",
            kind=TypeKind.PRIMITIVE,
            newtype_name="int32",
            source_type=int,
        )
        result = resolve_type_name(ti, "markdown")

        assert result == "int32"


class TestResolveTypeName:
    """Tests for resolve_type_name with list/optional flags."""

    def _make_type_info(self, **kwargs: object) -> TypeInfo:
        defaults = {"base_type": "str", "kind": TypeKind.PRIMITIVE}
        defaults.update(kwargs)
        return TypeInfo(**defaults)  # type: ignore[arg-type]

    def test_ignores_list_depth(self) -> None:
        """resolve_type_name returns the base type regardless of list_depth."""
        ti = self._make_type_info(list_depth=1)
        assert resolve_type_name(ti, "markdown") == "string"

    def test_ignores_is_optional(self) -> None:
        """resolve_type_name returns the base type regardless of is_optional."""
        ti = self._make_type_info(is_optional=True)
        assert resolve_type_name(ti, "markdown") == "string"


class TestIsStoragePrimitiveSource:
    def test_int32_is_storage_primitive(self) -> None:
        assert is_storage_primitive_source("int32") is True

    def test_int64_is_storage_primitive(self) -> None:
        assert is_storage_primitive_source("int64") is True

    def test_float64_is_storage_primitive(self) -> None:
        assert is_storage_primitive_source("float64") is True

    def test_str_is_storage_primitive(self) -> None:
        assert is_storage_primitive_source("str") is True

    def test_semantic_newtype_is_not(self) -> None:
        assert is_storage_primitive_source("HexColor") is False

    def test_none_is_not(self) -> None:
        assert is_storage_primitive_source(None) is False
