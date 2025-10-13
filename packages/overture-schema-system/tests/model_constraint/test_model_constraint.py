import pytest
from pydantic import BaseModel, Field, create_model

from overture.schema.system.model_constraint import apply_alias


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


# TODO - vic - In the next round, add back multi-constraint test cases
