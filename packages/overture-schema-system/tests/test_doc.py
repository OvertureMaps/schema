from enum import Enum

from pydantic import BaseModel, TypeAdapter

from overture.schema.system.doc import DocumentedEnum


class Color(str, DocumentedEnum):
    RED = ("red", "The color of blood")
    GREEN = "green"


class Priority(int, DocumentedEnum):
    LOW = 1
    HIGH = (10, "Reserved for system processes")


class HttpStatus(DocumentedEnum):
    OK = (200, "The request succeeded")


class Base(str, DocumentedEnum):
    """A member-less intermediate base."""


class Deep(Base):
    A = ("a", "The first letter")
    B = "b"


class TestStrMixin:
    def test_str_gives_value(self) -> None:
        assert str(Color.RED) == "red"
        assert str(Color.GREEN) == "green"

    def test_format_gives_value(self) -> None:
        assert f"{Color.RED}" == "red"
        assert format(Color.GREEN) == "green"

    def test_format_spec_applies_to_value(self) -> None:
        assert f"{Color.RED:>5}" == "  red"

    def test_percent_s_gives_value(self) -> None:
        assert "%s" % Color.RED == "red"  # noqa: UP031

    def test_repr_keeps_qualified_name(self) -> None:
        assert repr(Color.RED) == "<Color.RED: 'red'>"

    def test_documented_member(self) -> None:
        assert Color.RED.value == "red"
        assert Color.RED.__doc__ == "The color of blood"

    def test_undocumented_member(self) -> None:
        assert Color.GREEN.value == "green"
        assert Color.GREEN.__doc__ is None

    def test_lookup_by_value(self) -> None:
        assert Color("red") is Color.RED
        assert Color("green") is Color.GREEN

    def test_is_str(self) -> None:
        assert isinstance(Color.RED, str)
        assert Color.RED == "red"


class TestIntMixin:
    def test_str_gives_value(self) -> None:
        assert str(Priority.HIGH) == "10"
        assert str(Priority.LOW) == "1"

    def test_format_gives_value(self) -> None:
        assert f"{Priority.HIGH}" == "10"

    def test_format_spec_applies_to_value(self) -> None:
        assert format(Priority.HIGH, "03d") == "010"

    def test_repr_keeps_qualified_name(self) -> None:
        assert repr(Priority.HIGH) == "<Priority.HIGH: 10>"

    def test_documented_member(self) -> None:
        assert Priority.HIGH.__doc__ == "Reserved for system processes"
        assert Priority.LOW.__doc__ is None

    def test_lookup_by_value(self) -> None:
        assert Priority(10) is Priority.HIGH


class TestPlain:
    def test_str_keeps_qualified_name(self) -> None:
        assert str(HttpStatus.OK) == "HttpStatus.OK"
        assert f"{HttpStatus.OK}" == "HttpStatus.OK"

    def test_documented_member_and_lookup(self) -> None:
        assert HttpStatus(200) is HttpStatus.OK
        assert HttpStatus.OK.__doc__ == "The request succeeded"


class TestIntermediateBase:
    def test_subclass_builds_members_from_base_data_type(self) -> None:
        assert Deep("a") is Deep.A
        assert isinstance(Deep.A, str)

    def test_subclass_inherits_str_and_format(self) -> None:
        assert str(Deep.A) == "a"
        assert f"{Deep.B:>3}" == "  b"

    def test_subclass_keeps_member_docs(self) -> None:
        assert Deep.A.__doc__ == "The first letter"
        assert Deep.B.__doc__ is None


class TestPydantic:
    class Model(BaseModel):
        color: Color
        priority: Priority

    def test_validates_value_to_member(self) -> None:
        model = self.Model.model_validate({"color": "red", "priority": 10})
        assert model.color is Color.RED
        assert model.priority is Priority.HIGH

    def test_serializes_to_value(self) -> None:
        model = self.Model(color=Color.GREEN, priority=Priority.LOW)
        assert model.model_dump(mode="json") == {"color": "green", "priority": 1}
        assert model.model_dump_json() == '{"color":"green","priority":1}'

    def test_json_schema_matches_plain_mixin(self) -> None:
        class Plain(str, Enum):
            RED = "red"
            GREEN = "green"

        schema = TypeAdapter(Color).json_schema()
        plain = TypeAdapter(Plain).json_schema()
        plain["title"] = schema["title"]
        assert schema == plain
