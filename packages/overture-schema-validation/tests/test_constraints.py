from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.validation import (
    ConfidenceScoreConstraint,
)


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
