from typing import Annotated

import pytest
from pydantic import BaseModel, Field, ValidationError

from overture.schema.foundation.constraint import UniqueItemsConstraint


class TestUniqueItemsConstraint:
    """Test all collection-based constraints."""

    def test_valid(self) -> None:
        """Test UniqueItemsConstraint with unique items."""

        class TestModel(BaseModel):
            tags: Annotated[list[str], UniqueItemsConstraint()]

        valid_lists = [
            [],
            ["a"],
            ["a", "b", "c"],
            ["unique", "items", "only"],
        ]

        for items in valid_lists:
            model = TestModel(tags=items)
            assert model.tags == items

    def test_duplicates(self) -> None:
        """Test UniqueItemsConstraint with duplicate items."""

        class TestModel(BaseModel):
            tags: Annotated[list[str], UniqueItemsConstraint()]

        invalid_lists = [
            ["a", "a"],
            ["a", "b", "a"],
            ["duplicate", "values", "duplicate"],
        ]

        for items in invalid_lists:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(tags=items)
            assert "All items must be unique" in str(exc_info.value)

    def test_json_schema(self) -> None:
        """Test that the unique items constraint generates proper JSON Schema."""

    def test_collection_constraints_json_schema(self) -> None:
        class TestModel(BaseModel):
            unique_items: Annotated[list[str], UniqueItemsConstraint()]
            min_items: Annotated[
                list[str], UniqueItemsConstraint(), Field(min_length=2)
            ]
            max_items: Annotated[
                list[str], UniqueItemsConstraint(), Field(max_length=5)
            ]

        schema = TestModel.model_json_schema()
        props = schema["properties"]

        # Check collection constraints
        assert props["unique_items"].get("uniqueItems") is True
        assert props["min_items"].get("uniqueItems") is True
        assert props["min_items"].get("minItems") == 2
        assert props["max_items"].get("uniqueItems") is True
        assert props["max_items"].get("maxItems") == 5
