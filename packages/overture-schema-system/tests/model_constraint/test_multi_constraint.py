from pydantic import BaseModel
from util import assert_subset

from overture.schema.system.model_constraint import (
    FieldEqCondition,
    ForbidIfConstraint,
    MinFieldsSetConstraint,
    ModelConstraint,
    NoExtraFieldsConstraint,
    RadioGroupConstraint,
    RequireAnyOfConstraint,
    RequireIfConstraint,
    forbid_if,
    min_fields_set,
    no_extra_fields,
    radio_group,
    require_any_of,
    require_if,
)


def test_many_constraints():
    @forbid_if(["corge", "garply"], FieldEqCondition("qux", "hello"))
    @min_fields_set(3)
    @no_extra_fields
    @radio_group("foo", "bar", "baz")
    @require_any_of("foo", "corge")
    @require_if(["qux", "baz"], FieldEqCondition("corge", 42))
    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = None
        baz: bool | None = None
        qux: str | None = None
        corge: int | None = None
        garply: float | None = None

    # Verify that all the constraints are annotated.
    constraints = ModelConstraint.get_model_constraints(TestModel)
    expect_types = [
        ForbidIfConstraint,
        MinFieldsSetConstraint,
        NoExtraFieldsConstraint,
        RadioGroupConstraint,
        RequireAnyOfConstraint,
        RequireIfConstraint,
    ]
    assert len(expect_types) == len(constraints)
    for i, t in enumerate(reversed(expect_types)):
        assert isinstance(constraints[i], t)

    # Verify the JSON Schema.
    expect_json_schema = {
        "additionalProperties": False,
        "allOf": [
            {
                "if": {"properties": {"corge": {"const": 42}}},
                "then": {"required": ["qux", "baz"]},
            },
            {
                "if": {"properties": {"qux": {"const": "hello"}}},
                "then": {"not": {"required": ["corge", "garply"]}},
            },
        ],
        "anyOf": [{"required": ["foo"]}, {"required": ["corge"]}],
        "minProperties": 3,
        "oneOf": [
            {"properties": {"foo": {"const": True}}},
            {"properties": {"bar": {"const": True}}},
            {"properties": {"baz": {"const": True}}},
        ],
    }

    actual_json_schema = TestModel.model_json_schema()

    assert_subset(
        expect_json_schema,
        actual_json_schema,
        "expect_json_schema",
        "actual_json_schema",
    )

    # Verify a valid instance.
    TestModel(foo=None, bar=True, baz=False, qux="world", corge=42, garply=0.25)
