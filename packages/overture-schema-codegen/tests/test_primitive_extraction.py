"""Tests for primitive extraction and numeric bounds."""

from typing import Annotated, NewType

import overture.schema.system.primitive as _system_primitive
from overture.schema.codegen.extraction.newtype_extraction import extract_newtype
from overture.schema.codegen.extraction.primitive_extraction import (
    extract_numeric_bounds,
    extract_primitives,
    partition_primitive_and_geometry_names,
)
from overture.schema.codegen.extraction.specs import TypeIdentity
from overture.schema.codegen.extraction.type_analyzer import analyze_type
from overture.schema.system.primitive import float32, int32, int64, uint8
from pydantic import Field


class TestPartitionPrimitiveAndGeometryNames:
    """Tests for partition_primitive_and_geometry_names function."""

    def test_returns_type_identities(self) -> None:
        prims, geoms = partition_primitive_and_geometry_names(_system_primitive)
        assert all(isinstance(p, TypeIdentity) for p in prims)
        assert all(isinstance(g, TypeIdentity) for g in geoms)

    def test_identity_obj_is_actual_callable(self) -> None:
        prims, _ = partition_primitive_and_geometry_names(_system_primitive)
        int32_id = next(p for p in prims if p.name == "int32")
        assert int32_id.obj is _system_primitive.int32


class TestExtractPrimitives:
    """Tests for extract_primitives function."""

    def test_accepts_type_identities(self) -> None:
        prims, _ = partition_primitive_and_geometry_names(_system_primitive)
        specs = extract_primitives(prims)
        assert len(specs) > 0
        names = [s.name for s in specs]
        assert "int32" in names

    def test_extracts_bounds(self) -> None:
        prims, _ = partition_primitive_and_geometry_names(_system_primitive)
        specs = extract_primitives(prims)
        int32_spec = next(s for s in specs if s.name == "int32")
        assert int32_spec.bounds.ge == -(2**31)
        assert int32_spec.bounds.le == 2**31 - 1


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
