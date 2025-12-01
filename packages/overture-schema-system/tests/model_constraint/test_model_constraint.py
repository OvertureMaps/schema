import re
from typing import cast

import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonDict
from typing_extensions import override

from overture.schema.system import create_model
from overture.schema.system.metadata import Key, Metadata
from overture.schema.system.model_constraint import (
    Condition,
    FieldEqCondition,
    FieldGroupConstraint,
    ModelConstraint,
    Not,
    OptionalFieldGroupConstraint,
    apply_alias,
)
from overture.schema.system.model_constraint.model_constraint import (
    _MODEL_CONSTRAINT_KEY,
)

################################################################################
#                               ModelConstraint                                #
################################################################################


class TestModelConstraint:
    def test_init_error_invalid_name(self) -> None:
        with pytest.raises(
            TypeError, match="`name` must be a `str`, but 42 has type `int`"
        ):
            ModelConstraint(name=cast(str, 42))

    def test_init_valid_name(self) -> None:
        foo = ModelConstraint("foo")

        assert "foo" == foo.name

    def test_decorate_basic(self) -> None:
        class TestModel(BaseModel):
            pass

        constraint = ModelConstraint("foo")

        new_model = constraint.decorate(TestModel)
        assert new_model is not TestModel
        assert new_model.__name__ == TestModel.__name__
        assert new_model.__module__ == TestModel.__module__

        assert new_model.model_config == ConfigDict()

        metadata = Metadata.retrieve_from(new_model)
        assert metadata == {_MODEL_CONSTRAINT_KEY: (constraint,)}

    def test_decorate_prev_config(self) -> None:
        prev_config = ConfigDict(json_schema_extra={"foo": "bar"}, extra="allow")

        class TestModel(BaseModel):
            model_config = prev_config

        new_model = ModelConstraint("baz").decorate(TestModel)
        assert new_model is not TestModel
        assert new_model.__name__ == TestModel.__name__
        assert new_model.__module__ == TestModel.__module__
        assert new_model.model_config == prev_config
        assert new_model.model_config is not prev_config

    def test_decorate_prev_metadata(self) -> None:
        class TestModel(BaseModel):
            pass

        constraint = ModelConstraint("foo")

        extra_key = Key("foo")
        prev_metadata = Metadata({extra_key: "bar"})
        prev_metadata.attach_to(TestModel)

        new_model = constraint.decorate(TestModel)
        assert new_model is not TestModel
        assert new_model.__name__ == TestModel.__name__
        assert new_model.__module__ == TestModel.__module__

        new_metadata = Metadata.retrieve_from(new_model)
        assert {_MODEL_CONSTRAINT_KEY: (constraint,), extra_key: "bar"} == new_metadata

    @pytest.mark.parametrize(
        "model_class,expect",
        [
            (42, "`foo` can only be applied to classes"),
            (
                int,
                "`foo` target class must inherit from `pydantic.main.BaseModel`, but `int` does not",
            ),
        ],
    )
    def test_decorate_error_invalid_model_class_type(
        self, model_class: object, expect: str
    ) -> None:
        with pytest.raises(TypeError, match=expect):
            ModelConstraint("foo").decorate(cast(type[BaseModel], model_class))

    def test_decorate_error_invalid_model_class(self) -> None:
        class TestModel(BaseModel):
            pass

        class TestConstraint(ModelConstraint):
            @override
            def validate_class(self, model_class: type[BaseModel]) -> None:
                raise TypeError("bar!")

        with pytest.raises(TypeError, match="bar!"):
            TestConstraint().decorate(cast(type[BaseModel], TestModel))


################################################################################
#                            FieldGroupConstraint                              #
################################################################################


class TestFieldGroupConstraint:
    def test_init_error_field_names_not_tuple(self) -> None:
        with pytest.raises(
            TypeError, match="`field_names` must be a `tuple`, but 42 has type `int`"
        ):
            FieldGroupConstraint("foo", cast(tuple[str, ...], 42))

    def test_init_error_field_empty(self) -> None:
        with pytest.raises(
            ValueError, match="`field_names` cannot be empty, but it is"
        ):
            FieldGroupConstraint("foo", ())

    def test_init_error_field_names_not_all_str(self) -> None:
        with pytest.raises(
            TypeError,
            match=re.escape(
                "`field_names` must contain only `str` values, but ('bar', 42) contains at least one non-`str` value"
            ),
        ):
            FieldGroupConstraint("foo", cast(tuple[str, ...], ("bar", 42)))

    def test_init_error_field_names_duplicated(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "`field_names` must not contain duplicates, but ('bar', 'bar') contains at least one repeated value"
            ),
        ):
            FieldGroupConstraint("foo", ("bar", "bar"))

    @pytest.mark.parametrize(
        "field_names",
        [
            ("bar",),
            ("baz", "bar"),
        ],
    )
    def test_init_valid_field_names(self, field_names: tuple[str, ...]) -> None:
        constraint = FieldGroupConstraint("foo", field_names)

        assert field_names == constraint.field_names

    @pytest.mark.parametrize(
        "field_names",
        [
            ("baz",),
            ("foo", "baz"),
            ("bar", "foo", "qux"),
        ],
    )
    def test_validate_class_error_field_name_not_in_model(
        self, field_names: tuple[str, ...]
    ) -> None:
        class TestModel(BaseModel):
            foo: int
            bar: int

        constraint = FieldGroupConstraint("Hello", field_names)
        with pytest.raises(
            TypeError,
            match="`Hello` specifies one or more fields that are not in the model class `TestModel`",
        ):
            constraint.decorate(TestModel)

    @pytest.mark.parametrize(
        "field_names",
        [
            ("foo",),
            ("foo", "bar"),
            ("bar",),
            ("bar", "foo"),
        ],
    )
    def test_validate_class_success(self, field_names: tuple[str, ...]) -> None:
        class TestModel(BaseModel):
            foo: int
            bar: int

        FieldGroupConstraint("Hello", field_names).decorate(TestModel)


################################################################################
#                        OptionalFieldGroupConstraint                          #
################################################################################


class TestOptionalFieldGroupConstraint:
    @pytest.mark.parametrize(
        "field_names",
        [
            ("foo",),
            ("foo", "bar"),
            ("foo", "baz"),
            ("foo", "bar", "baz"),
        ],
    )
    def test_validate_class_error_field_name_not_optional_in_model(
        self, field_names: tuple[str, ...]
    ) -> None:
        class TestModel(BaseModel):
            foo: int
            bar: int | None = None
            baz: str | None = None

        constraint = OptionalFieldGroupConstraint("Hello", field_names)

        with pytest.raises(
            TypeError,
            match="`Hello` expects all the fields to be optional, but at least one is required in the model class `TestModel`",
        ):
            constraint.decorate(TestModel)

    @pytest.mark.parametrize(
        "field_names",
        [
            ("foo",),
            ("foo", "bar"),
            ("bar",),
            ("bar", "foo"),
        ],
    )
    def test_validate_class_success(self, field_names: tuple[str, ...]) -> None:
        class TestModel(BaseModel):
            foo: int | None = None
            bar: str | None = None

        OptionalFieldGroupConstraint("Hello", field_names).decorate(TestModel)


################################################################################
#                                    Not                                       #
################################################################################


class TestNot:
    @pytest.mark.parametrize(
        "condition",
        [
            (FieldEqCondition("foo", 42),),
            (FieldEqCondition("foo", "bar"),),
        ],
    )
    def test_repr(self, condition: Condition) -> None:
        not_condition = Not(condition)

        assert repr(not_condition) == "Not(" + repr(condition) + ")"

    @pytest.mark.parametrize(
        "condition",
        [
            (FieldEqCondition("foo", 42),),
            (FieldEqCondition("foo", "bar"),),
        ],
    )
    def test_negate(self, condition: Condition) -> None:
        not_condition = Not(condition)

        assert not_condition.negate() is condition
        assert ~not_condition is condition


################################################################################
#                              FieldEqCondition                                #
################################################################################


class TestFieldEqCondition:
    def test_init_error_field_name_not_str(self) -> None:
        with pytest.raises(
            TypeError, match="`field_name` must be a `str`, but 42 is a int"
        ):
            FieldEqCondition(cast(str, 42), "foo")

    def test_validate_class_error_field_name_not_in_model(self) -> None:
        class TestModel(BaseModel):
            foo: int

        condition = FieldEqCondition("bar", 42)

        with pytest.raises(
            TypeError,
            match="model class `TestModel` must contain the condition field 'bar', but it does not",
        ):
            condition.validate_class(TestModel)

    def test_validate_class_success(self) -> None:
        class TestModel(BaseModel):
            foo: int

        FieldEqCondition("foo", 42).validate_class(TestModel)

    @pytest.mark.parametrize(
        "condition,expect",
        [
            (FieldEqCondition("foo", 42), True),
            (FieldEqCondition("foo", "bar"), False),
        ],
    )
    def test_eval(self, condition: FieldEqCondition, expect: bool) -> None:
        class TestModel(BaseModel):
            foo: int

        model_instance = TestModel(foo=42)

        assert condition.eval(model_instance) is expect
        assert (~condition).eval(model_instance) is not expect
        assert condition.negate().eval(model_instance) is not expect

    @pytest.mark.parametrize(
        "condition,expect",
        [
            (FieldEqCondition("foo", 42), {"properties": {"foo": {"const": 42}}}),
            (
                Not(FieldEqCondition("bar", "qux")),
                {"not": {"properties": {"baz": {"const": "qux"}}}},
            ),
        ],
    )
    def test_json_schema(self, condition: Condition, expect: JsonDict) -> None:
        class TestModel(BaseModel):
            foo: int
            bar: str = Field(alias="baz")

        actual = condition.json_schema(TestModel)

        assert expect == actual


################################################################################
#                                 apply_alias                                  #
################################################################################


@pytest.mark.parametrize(
    "model_class,field_name,expect",
    [
        (create_model("case1", foo=(str, ...)), "foo", "foo"),
        (create_model("case2", foo=(str, Field(alias="FOO"))), "foo", "FOO"),
        (
            create_model("case3", foo=(str, ...), bar=(str, Field(alias="bAr"))),
            "foo",
            "foo",
        ),
        (
            create_model("case4", foo=(str, ...), bar=(str, Field(alias="bAr"))),
            "bar",
            "bAr",
        ),
    ],
)
def test_apply_alias_success(
    model_class: type[BaseModel], field_name: str, expect: str
) -> None:
    actual = apply_alias(model_class, field_name)

    assert expect == actual


@pytest.mark.parametrize(
    "model_class,field_name",
    [
        (create_model("case1"), "foo"),
        (create_model("case1", foo=(str, ...)), "bar"),
    ],
)
def test_apply_alias_error_no_such_field(
    model_class: type[BaseModel], field_name: str
) -> None:
    with pytest.raises(
        ValueError, match=f"does not contain a field named '{field_name}'"
    ):
        apply_alias(model_class, field_name)
