import pytest
from pydantic import BaseModel, ConfigDict, create_model
from util import assert_subset

from overture.schema.system.model_constraint import (
    NoExtraFieldsConstraint,
    no_extra_fields,
)


def test_error_invalid_model_class() -> None:
    expect_pattern = r"can't apply `@?\w+` to model class `TestModel`: existing `model_config\['extra'\]` is already set to '\w+'"

    with pytest.raises(TypeError, match=expect_pattern):

        @no_extra_fields
        class TestModel(BaseModel):
            model_config = ConfigDict(extra="ignore")

    with pytest.raises(TypeError, match=expect_pattern):

        class TestModel(BaseModel):
            model_config = ConfigDict(extra="allow")

        NoExtraFieldsConstraint().validate_class(TestModel)


@pytest.mark.parametrize(
    "model_class",
    [
        create_model("case1"),
        create_model("case2", __config__=ConfigDict()),
        create_model("case3", __config__=ConfigDict(extra=None)),
        create_model("case4", __config__=ConfigDict(extra="forbid")),
    ],
)
def test_valid_model_class(model_class: type[BaseModel]) -> None:
    decorated_class = NoExtraFieldsConstraint().decorate(model_class)

    assert "forbid" == decorated_class.model_config["extra"]
    assert_subset(
        {"additionalProperties": False},
        decorated_class.model_json_schema(),
        "expect",
        "actual",
    )
