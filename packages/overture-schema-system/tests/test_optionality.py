import json
import sys
from pathlib import Path
from types import NoneType
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, create_model
from pydantic.json_schema import JsonDict

from overture.schema.system.optionality import Omitable

sys.path.insert(0, str(Path(__file__).parent.parent))  # Needed to import `util` module.

from util import assert_subset


@pytest.mark.parametrize(
    "model,expect_json,expect_json_schema",
    [
        (
            create_model("case1", foo=Omitable[int])(),
            {},
            {
                "properties": {
                    "foo": {
                        "type": "integer",
                    }
                },
            },
        ),
        (
            create_model("case2", foo=Omitable[int])(foo=42),
            {"foo": 42},
            {
                "properties": {
                    "foo": {
                        "type": "integer",
                    }
                },
            },
        ),
        (
            create_model("case3", foo=Omitable[int | str])(),
            {},
            {
                "properties": {
                    "foo": {
                        "anyOf": [
                            {"type": "integer"},
                            {"type": "string"},
                        ]
                    }
                },
            },
        ),
        (
            create_model("case3", foo=Omitable[int | str])(foo="bar"),
            {"foo": "bar"},
            {
                "properties": {
                    "foo": {
                        "anyOf": [
                            {"type": "integer"},
                            {"type": "string"},
                        ]
                    }
                },
            },
        ),
    ],
)
def test_omitable_model(
    model: type[BaseModel], expect_json: JsonDict, expect_json_schema: JsonDict
) -> None:
    actual_json = json.loads(model.model_dump_json())
    assert expect_json == actual_json

    actual_json_schema = model.model_json_schema()
    assert_subset(
        expect_json_schema,
        actual_json_schema,
        "expect_json_schema",
        "actual_json_schema",
    )

    assert not model.__class__.model_fields["foo"].is_required()


@pytest.mark.parametrize(
    "item",
    [
        None,
        None | int,
        str | None,
        Annotated[None, "something"],
        Annotated[int | str | None, "something"],
        int | bool | Annotated[None, "something"],
        Annotated[
            int | bool | Annotated[Annotated[float | NoneType, "innermost"], "middle"],
            "outermost",
        ],
    ],
)
def test_omitable_type_error(item: Any) -> None:
    with pytest.raises(TypeError, match="`None` not allowed in `Omitable` args"):
        Omitable[item]
