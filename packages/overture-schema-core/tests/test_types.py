from typing import Annotated

import pytest
from overture.schema.core.types import LinearReferenceRangeConstraint
from pydantic import BaseModel, ValidationError


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
