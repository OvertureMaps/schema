from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.validation import (
    CategoryPatternConstraint,
    ConfidenceScoreConstraint,
    LinearReferenceRangeConstraint,
)


class TestCategoryPatternConstraint:
    def test_category_pattern_constraint_valid(self) -> None:
        """Test CategoryPatternConstraint with valid snake_case patterns."""

        class TestModel(BaseModel):
            category: Annotated[str, CategoryPatternConstraint()]

        valid_categories = [
            "restaurant",
            "gas_station",
            "shopping_mall",
            "coffee_shop",
            "bank_atm",
        ]

        for cat in valid_categories:
            model = TestModel(category=cat)
            assert model.category == cat

    def test_category_pattern_constraint_invalid(self) -> None:
        """Test CategoryPatternConstraint with invalid category patterns."""

        class TestModel(BaseModel):
            category: Annotated[str, CategoryPatternConstraint()]

        invalid_categories = [
            "Restaurant",  # Capital letter
            "gas-station",  # Hyphen instead of underscore
            "shopping mall",  # Space instead of underscore
            "category!",  # Special character
        ]

        for cat in invalid_categories:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(category=cat)
            assert "Invalid category format" in str(exc_info.value)


class TestNumericConstraints:
    """Test all numeric constraints."""

    def test_confidence_score_constraint_valid(self) -> None:
        """Test ConfidenceScoreConstraint with valid scores (0.0 to 1.0)."""

        class TestModel(BaseModel):
            confidence: Annotated[float, ConfidenceScoreConstraint()]

        valid_scores = [0.0, 0.1, 0.5, 0.9, 1.0, 0.123456]

        for score in valid_scores:
            model = TestModel(confidence=score)
            assert model.confidence == score

    def test_confidence_score_constraint_invalid(self) -> None:
        """Test ConfidenceScoreConstraint with invalid scores."""

        class TestModel(BaseModel):
            confidence: Annotated[float, ConfidenceScoreConstraint()]

        invalid_scores = [-0.1, 1.1, 2.0, -1.0, 10.0]

        for score in invalid_scores:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(confidence=score)
            # Check for Pydantic's built-in error messages
            assert "greater than or equal to 0" in str(
                exc_info.value
            ) or "less than or equal to 1" in str(exc_info.value)


class TestSpecializedConstraints:
    """Test specialized constraints."""

    def test_linear_reference_range_constraint_valid(self) -> None:
        """Test LinearReferenceRangeConstraint with valid ranges."""

        class TestModel(BaseModel):
            range_val: Annotated[list[float], LinearReferenceRangeConstraint()]

        valid_ranges = [
            [0.0, 1.0],
            [0.1, 0.9],
            [0.0, 0.5],
            [0.25, 0.75],
        ]

        for range_val in valid_ranges:
            model = TestModel(range_val=range_val)
            assert model.range_val == range_val

    def test_linear_reference_range_constraint_invalid(self) -> None:
        """Test LinearReferenceRangeConstraint with invalid ranges."""

        class TestModel(BaseModel):
            range_val: Annotated[list[float], LinearReferenceRangeConstraint()]

        invalid_ranges = [
            [0.9, 0.1],  # start > end
            [-0.1, 0.5],  # start < 0
            [0.5, 1.1],  # end > 1
            [0.5, 0.5],  # start == end
            [0.0],  # Wrong length
            [0.0, 0.5, 1.0],  # Wrong length
        ]

        for range_val in invalid_ranges:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(range_val=range_val)
            # Check that validation fails with appropriate error
            assert len(exc_info.value.errors()) > 0
