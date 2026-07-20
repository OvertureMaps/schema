"""Tests for union extraction."""

import re
from typing import Any

import pytest
from annotated_types import MinLen
from codegen_test_support import (
    LongNamesSegment,
    RailSegment,
    RoadSegment,
    SegmentBase,
    ShortNamesSegment,
    TestEnumDiscriminatorUnion,
    TestSegment,
    TestSegmentDivergingConstraints,
    TestSegmentEqualConstraints,
    WaterSegment,
)
from overture.schema.codegen.extraction.field import (
    ArrayOf,
    ConstraintSource,
    Primitive,
)
from overture.schema.codegen.extraction.length_constraints import ArrayMinLen
from overture.schema.codegen.extraction.specs import FieldSpec, UnionSpec
from overture.schema.codegen.extraction.union_extraction import (
    _constraints_fingerprint,
    extract_union,
)
from overture.schema.common.scoping.vehicle import VehicleSelector
from overture.schema.system.field_constraint import (
    FieldConstraint,
    UniqueItemsConstraint,
)
from overture.schema.system.field_constraint.string import (
    CountryCodeAlpha2Constraint,
    JsonPointerConstraint,
    PatternConstraint,
)
from pydantic import Field, GetCoreSchemaHandler
from pydantic_core import core_schema


class TestExtractUnion:
    """Tests for extract_union function."""

    @pytest.fixture
    def segment_spec(self) -> UnionSpec:
        return extract_union("TestSegment", TestSegment)

    def test_extracts_name_and_description(self, segment_spec: UnionSpec) -> None:
        """UnionSpec captures the union name and docstring."""
        assert segment_spec.name == "TestSegment"
        assert segment_spec.description == "Test segment union"

    def test_finds_common_base(self, segment_spec: UnionSpec) -> None:
        """Identifies SegmentBase as the common base class."""
        assert segment_spec.common_base is SegmentBase

    def test_shared_fields_first(self, segment_spec: UnionSpec) -> None:
        """Shared fields from common base come first with variant_sources=None."""
        shared = [
            af for af in segment_spec.annotated_fields if af.variant_sources is None
        ]
        shared_names = [af.field_spec.name for af in shared]
        assert "geometry" in shared_names
        assert "subtype" in shared_names
        # Shared fields are at the start
        first_variant_idx = next(
            (
                i
                for i, af in enumerate(segment_spec.annotated_fields)
                if af.variant_sources is not None
            ),
            len(segment_spec.annotated_fields),
        )
        for af in segment_spec.annotated_fields[:first_variant_idx]:
            assert af.variant_sources is None

    def test_variant_specific_fields_have_sources(
        self, segment_spec: UnionSpec
    ) -> None:
        """Variant-only fields carry their source classes."""
        speed = next(
            af
            for af in segment_spec.annotated_fields
            if af.field_spec.name == "speed_limit"
        )
        assert speed.variant_sources == (RoadSegment,)
        gauge = next(
            af
            for af in segment_spec.annotated_fields
            if af.field_spec.name == "rail_gauge"
        )
        assert gauge.variant_sources == (RailSegment,)

    def test_heterogeneous_same_name_produces_separate_rows(
        self, segment_spec: UnionSpec
    ) -> None:
        """class_ in Road (str) vs Rail (int): separate rows, not merged."""
        class_fields = [
            af for af in segment_spec.annotated_fields if af.field_spec.name == "class"
        ]
        assert len(class_fields) == 2
        sources = {af.variant_sources for af in class_fields}
        assert (RoadSegment,) in sources
        assert (RailSegment,) in sources

    def test_members_lists_all_member_classes(self, segment_spec: UnionSpec) -> None:
        """UnionSpec.members contains all union member classes."""
        assert set(segment_spec.members) == {RoadSegment, RailSegment, WaterSegment}

    def test_source_annotation_preserved(self, segment_spec: UnionSpec) -> None:
        """source_annotation holds the original Annotated[Union[...]]."""
        assert segment_spec.source_annotation is TestSegment

    def test_fields_property_returns_plain_list(self, segment_spec: UnionSpec) -> None:
        """spec.fields returns list[FieldSpec] without provenance."""
        for f in segment_spec.fields:
            assert isinstance(f, FieldSpec)


class TestExtractDiscriminatorWithEnumLiterals:
    """Discriminator mapping uses runtime string values for enum literals."""

    @pytest.fixture
    def spec(self) -> UnionSpec:
        return extract_union("TestEnumDiscriminatorUnion", TestEnumDiscriminatorUnion)

    def test_discriminator_mapping_uses_enum_values(self, spec: UnionSpec) -> None:
        """Mapping keys must be the Parquet-serialized string values, not enum repr."""
        assert spec.discriminator_mapping is not None
        assert set(spec.discriminator_mapping.keys()) == {"car", "bike"}


class TestDivergingConstraints:
    """Same-named fields with matching shape but diverging constraints split
    into separate arm-gated `AnnotatedField`s rather than raising.

    Field-level checks are already arm-gated by `Guard`s built from
    `variant_sources` (see `check_builder._field_checks_for_union`), and the
    renderer's collision resolver already disambiguates multiple `Check`s
    that land on the same field label (e.g. the pre-existing `value_0`/
    `value_1` split for a field required only on some arms). Keeping
    diverging-constraint fields as separate rows reuses that machinery
    instead of dropping one arm's constraints or refusing to extract.
    """

    def test_diverging_constraints_produce_separate_annotated_fields(self) -> None:
        """`ShortNamesSegment` and `LongNamesSegment` both declare `aliases`
        as `list[str] | None` -- structurally identical -- but their
        `min_length` constraints differ (1 vs 5). Extraction keeps them as
        two `AnnotatedField`s, each gated to the arm that declared it.
        """
        spec = extract_union(
            "TestSegmentDivergingConstraints", TestSegmentDivergingConstraints
        )
        aliases_fields = [
            af for af in spec.annotated_fields if af.field_spec.name == "aliases"
        ]
        assert len(aliases_fields) == 2

        by_source = {af.variant_sources: af for af in aliases_fields}
        assert (ShortNamesSegment,) in by_source
        assert (LongNamesSegment,) in by_source

        def min_length(af: object) -> int:
            for cs in af.field_spec.shape.constraints:  # type: ignore[attr-defined]
                if isinstance(cs.constraint, ArrayMinLen):
                    return cs.constraint.min_length  # type: ignore[no-any-return]
            raise AssertionError("no ArrayMinLen constraint found")

        assert min_length(by_source[(ShortNamesSegment,)]) == 1
        assert min_length(by_source[(LongNamesSegment,)]) == 5

    def test_diverging_constraints_do_not_raise(self) -> None:
        """Extraction succeeds where it previously raised ValueError."""
        extract_union(
            "TestSegmentDivergingConstraints", TestSegmentDivergingConstraints
        )


class TestUnionNameDerivation:
    """Union name fallback when the caller passes a member class name."""

    def test_name_derived_from_common_base(self) -> None:
        """When name matches a member class, derive from common base minus 'Base' suffix."""
        spec = extract_union("VehicleAxleCountSelector", VehicleSelector)
        assert spec.name == "VehicleSelector"


def _make_array_field(constraint: object) -> FieldSpec:
    """Build a FieldSpec with one array-level constraint for fingerprint tests."""
    cs = ConstraintSource(source_ref=None, source_name=None, constraint=constraint)
    return FieldSpec(
        name="items", shape=ArrayOf(element=Primitive("str"), constraints=(cs,))
    )


def _make_scalar_field(constraint: object) -> FieldSpec:
    """Build a FieldSpec with one scalar-level constraint for fingerprint tests."""
    cs = ConstraintSource(source_ref=None, source_name=None, constraint=constraint)
    return FieldSpec(name="tag", shape=Primitive("str", constraints=(cs,)))


class _ListAttrConstraint(FieldConstraint):
    """Test-only constraint with a list-valued attribute (fingerprint hashability guard)."""

    def __init__(self, items: list[str]) -> None:
        self.items = list(items)

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return handler(source)


class TestConstraintsFingerprint:
    """_constraints_fingerprint produces value-stable keys across distinct instances."""

    def test_marker_constraint_equal_instances_same_fingerprint(self) -> None:
        """Two distinct UniqueItemsConstraint() instances fingerprint equal."""
        fs1 = _make_array_field(UniqueItemsConstraint())
        fs2 = _make_array_field(UniqueItemsConstraint())
        assert _constraints_fingerprint(fs1) == _constraints_fingerprint(fs2)

    def test_parametric_constraint_equal_instances_same_fingerprint(self) -> None:
        """Two distinct CountryCodeAlpha2Constraint() instances fingerprint equal."""
        fs1 = _make_scalar_field(CountryCodeAlpha2Constraint())
        fs2 = _make_scalar_field(CountryCodeAlpha2Constraint())
        assert _constraints_fingerprint(fs1) == _constraints_fingerprint(fs2)

    def test_different_attribute_values_unequal_fingerprint(self) -> None:
        """Constraints differing in attribute value produce different fingerprints."""
        fs1 = _make_array_field(MinLen(1))
        fs2 = _make_array_field(MinLen(5))
        assert _constraints_fingerprint(fs1) != _constraints_fingerprint(fs2)

    def test_equal_constraints_do_not_raise(self) -> None:
        """Union extraction does not raise when members share a field with equal constraints."""
        extract_union("TestSegmentEqualConstraints", TestSegmentEqualConstraints)

    def test_different_zero_attr_constraint_classes_unequal(self) -> None:
        """Two different marker constraint classes with no attributes fingerprint unequal.

        Both `UniqueItemsConstraint()` and `JsonPointerConstraint()` have no
        instance attributes, so their keys differ only by qualified class name.
        """
        fs1 = _make_array_field(UniqueItemsConstraint())
        fs2 = _make_array_field(JsonPointerConstraint())
        assert _constraints_fingerprint(fs1) != _constraints_fingerprint(fs2)

    def test_pattern_constraint_flags_distinguish_fingerprint(self) -> None:
        """PatternConstraints with the same source but different flags diverge.

        Value equality on `PatternConstraint` normalizes the compiled
        `re.Pattern` to `(pattern, flags)`, so a flag difference produces
        distinct fingerprints rather than collapsing.
        """
        fs1 = _make_scalar_field(PatternConstraint(r"^[a-z]+$", "err"))
        fs2 = _make_scalar_field(PatternConstraint(r"^[a-z]+$", "err", re.IGNORECASE))
        assert _constraints_fingerprint(fs1) != _constraints_fingerprint(fs2)

    def test_distinct_value_eq_constraints_diverge(self) -> None:
        """Same type, different attributes diverge -- the case dedup guards.

        Per-variant divergence on a structurally identical field is the
        condition `_constraints_fingerprint` exists to catch. Two
        `PatternConstraint`s differing only in source pattern must not collapse.
        """
        fs1 = _make_scalar_field(PatternConstraint(r"^[a-z]+$", "err"))
        fs2 = _make_scalar_field(PatternConstraint(r"^[0-9]+$", "err"))
        assert _constraints_fingerprint(fs1) != _constraints_fingerprint(fs2)

    def test_container_valued_constraint_routes_through_fingerprint(self) -> None:
        """A container-valued constraint builds a frozenset without raising.

        Guards the original failure mode: an unhashable constraint key crashed
        `frozenset` construction in `_constraints_fingerprint`. Value `__hash__`
        on the constraint normalizes the list attribute, so equal instances
        both hash and collapse.
        """
        fs1 = _make_array_field(_ListAttrConstraint(["a", "b"]))
        fs2 = _make_array_field(_ListAttrConstraint(["a", "b"]))
        assert _constraints_fingerprint(fs1) == _constraints_fingerprint(fs2)

    def test_foreign_identity_eq_metadata_equal_instances_collapse(self) -> None:
        """Raw pydantic `Field(...)` metadata compares by identity but collapses.

        Pydantic's internal metadata is the lone constraint type that falls
        back to identity equality, so two equal-valued instances would
        fingerprint as divergent. `_fingerprint_key` keys it on its
        value-stable `repr` so equal metadata still collapses.
        """
        raw1 = Field(pattern=r"^[a-z]+$").metadata[0]
        raw2 = Field(pattern=r"^[a-z]+$").metadata[0]
        assert raw1 != raw2
        fs1 = _make_scalar_field(raw1)
        fs2 = _make_scalar_field(raw2)
        assert _constraints_fingerprint(fs1) == _constraints_fingerprint(fs2)

    def test_foreign_identity_eq_metadata_distinct_values_diverge(self) -> None:
        """Different raw `Field(...)` patterns produce divergent fingerprints."""
        fs1 = _make_scalar_field(Field(pattern=r"^[a-z]+$").metadata[0])
        fs2 = _make_scalar_field(Field(pattern=r"^[0-9]+$").metadata[0])
        assert _constraints_fingerprint(fs1) != _constraints_fingerprint(fs2)
