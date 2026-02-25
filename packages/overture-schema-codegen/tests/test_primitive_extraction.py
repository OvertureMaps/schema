"""Tests for primitive extraction and numeric bounds."""

from typing import Annotated, NewType

from overture.schema.codegen.newtype_extraction import extract_newtype
from overture.schema.codegen.primitive_extraction import extract_numeric_bounds
from overture.schema.codegen.type_analyzer import analyze_type
from overture.schema.system.primitive import float32, int32, int64, uint8
from pydantic import Field


class TestExtractNumericBounds:
    """Tests for extract_numeric_bounds function."""

    def test_signed_integer_bounds(self) -> None:
        """Should extract ge/le from a constrained integer NewType."""
        spec = extract_newtype(int32)
        bounds = extract_numeric_bounds(spec.type_info)

        assert bounds.ge == -(2**31)
        assert bounds.le == 2**31 - 1

    def test_unsigned_integer_bounds(self) -> None:
        """Should extract 0-based bounds from unsigned NewType."""
        spec = extract_newtype(uint8)
        bounds = extract_numeric_bounds(spec.type_info)

        assert bounds.ge == 0
        assert bounds.le == 255

    def test_int64_bounds(self) -> None:
        """Should extract large bounds from int64."""
        spec = extract_newtype(int64)
        bounds = extract_numeric_bounds(spec.type_info)

        assert bounds.ge == -(2**63)
        assert bounds.le == 2**63 - 1

    def test_unconstrained_type(self) -> None:
        """Should return empty Interval for types without numeric constraints."""
        spec = extract_newtype(float32)
        bounds = extract_numeric_bounds(spec.type_info)

        assert bounds.ge is None
        assert bounds.gt is None
        assert bounds.le is None
        assert bounds.lt is None

    def test_exclusive_bounds(self) -> None:
        """Should extract gt/lt from constraints using exclusive bounds."""
        ExclusiveBounded = NewType(
            "ExclusiveBounded", Annotated[int, Field(gt=0, lt=100)]
        )
        type_info = analyze_type(ExclusiveBounded)
        bounds = extract_numeric_bounds(type_info)

        assert bounds.gt == 0
        assert bounds.lt == 100
        assert bounds.ge is None
        assert bounds.le is None

    def test_mixed_bounds(self) -> None:
        """Should extract a mix of inclusive and exclusive bounds."""
        MixedBounded = NewType("MixedBounded", Annotated[int, Field(ge=0, lt=256)])
        type_info = analyze_type(MixedBounded)
        bounds = extract_numeric_bounds(type_info)

        assert bounds.ge == 0
        assert bounds.lt == 256
        assert bounds.gt is None
        assert bounds.le is None
