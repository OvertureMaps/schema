"""Tests for enum extraction."""

from enum import Enum

from codegen_test_support import find_member
from overture.schema.codegen.extraction.enum_extraction import extract_enum
from overture.schema.codegen.extraction.specs import EnumMemberSpec, EnumSpec
from overture.schema.system.doc import DocumentedEnum


class TestEnumMemberSpec:
    """Tests for EnumMemberSpec dataclass."""

    def test_stores_name_value_description(self) -> None:
        """EnumMemberSpec should store name, value, and description."""
        member = EnumMemberSpec(
            name="GABLED", value="gabled", description="A gabled roof"
        )

        assert member.name == "GABLED"
        assert member.value == "gabled"
        assert member.description == "A gabled roof"

    def test_description_can_be_none(self) -> None:
        """EnumMemberSpec description should be optional."""
        member = EnumMemberSpec(name="FLAT", value="flat", description=None)

        assert member.description is None


class TestEnumSpec:
    """Tests for EnumSpec dataclass."""

    def test_stores_name_description_members(self) -> None:
        """EnumSpec should store name, description, and members list."""
        members = [
            EnumMemberSpec(name="A", value="a", description=None),
            EnumMemberSpec(name="B", value="b", description="The letter B"),
        ]

        spec = EnumSpec(
            name="Letters", description="A collection of letters", members=members
        )

        assert spec.name == "Letters"
        assert spec.description == "A collection of letters"
        assert len(spec.members) == 2


class TestExtractEnumSimple:
    """Tests for extract_enum with simple str Enum classes."""

    def test_extracts_simple_str_enum(self) -> None:
        """Should extract name, description, and members from simple str Enum."""

        class RoofShape(str, Enum):
            """The shape of the roof."""

            FLAT = "flat"
            GABLED = "gabled"
            DOMED = "dome"

        result = extract_enum(RoofShape)

        assert result.name == "RoofShape"
        assert result.description == "The shape of the roof."
        assert len(result.members) == 3

        # Check member extraction
        flat = find_member(result, "FLAT")
        assert flat.value == "flat"
        assert flat.description is None

        gabled = find_member(result, "GABLED")
        assert gabled.value == "gabled"

    def test_enum_without_docstring(self) -> None:
        """Should handle enum without docstring."""

        class SimpleEnum(str, Enum):
            A = "a"
            B = "b"

        result = extract_enum(SimpleEnum)

        assert result.name == "SimpleEnum"
        assert result.description is None


class TestExtractEnumDocumented:
    """Tests for extract_enum with DocumentedEnum classes."""

    def test_extracts_documented_enum_with_member_descriptions(self) -> None:
        """Should extract per-member descriptions from DocumentedEnum."""

        class Side(str, DocumentedEnum):
            """The side on which something appears."""

            LEFT = ("left", "On the left side")
            RIGHT = ("right", "On the right side")

        result = extract_enum(Side)

        assert result.name == "Side"
        assert result.description == "The side on which something appears."
        assert len(result.members) == 2

        left = find_member(result, "LEFT")
        assert left.value == "left"
        assert left.description == "On the left side"

        right = find_member(result, "RIGHT")
        assert right.value == "right"
        assert right.description == "On the right side"

    def test_documented_enum_with_mixed_documentation(self) -> None:
        """DocumentedEnum can have some members documented and others not."""

        class ConnectionState(str, DocumentedEnum):
            """Connection states."""

            CONNECTED = "connected"
            DISCONNECTED = "disconnected"
            QUIESCING = ("quiescing", "Gracefully shutting down")

        result = extract_enum(ConnectionState)

        connected = find_member(result, "CONNECTED")
        assert connected.value == "connected"
        assert connected.description is None

        quiescing = find_member(result, "QUIESCING")
        assert quiescing.value == "quiescing"
        assert quiescing.description == "Gracefully shutting down"


class TestEnumSpecSourceType:
    """Tests for source_type on EnumSpec."""

    def test_enum_spec_source_type_defaults_to_none(self) -> None:
        spec = EnumSpec(name="Test", description=None)
        assert spec.source_type is None

    def test_extract_enum_sets_source_type(self) -> None:
        class Color(str, Enum):
            RED = "red"

        spec = extract_enum(Color)
        assert spec.source_type is Color
