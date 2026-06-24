"""Tests for valid-row generation from ModelSpecs."""

import uuid
from enum import Enum

import pytest
from annotated_types import Gt, Lt
from codegen_test_support import (
    FeatureWithDict,
    FeatureWithRequiredUrl,
    discover_feature,
    spec_for_model,
)
from overture.schema.codegen.extraction.field import (
    AnyScalar,
    ConstraintSource,
    LiteralScalar,
    ModelRef,
    Primitive,
)
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.specs import (
    FieldSpec,
    ModelSpec,
    UnionSpec,
)
from overture.schema.codegen.pyspark.constraint_dispatch import ExpressionDescriptor
from overture.schema.codegen.pyspark.test_data.base_row import (
    _primitive_default,
    _value_from_check_pattern,
    _value_from_scalar_constraints,
    generate_arm_rows,
    generate_base_row,
    generate_populated_arm_rows,
    generate_populated_row,
    value_for_field,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    forbid_if,
    require_if,
)
from pydantic import BaseModel, Field, HttpUrl, TypeAdapter


@pytest.fixture(scope="module")
def connector_spec() -> ModelSpec:
    return discover_feature("Connector")


@pytest.fixture(scope="module")
def segment_spec() -> ModelSpec:
    return discover_feature("Segment")


@pytest.fixture(scope="module")
def segment_union(segment_spec: ModelSpec) -> UnionSpec:
    assert isinstance(segment_spec, UnionSpec)
    return segment_spec


class TestPrimitiveDefault:
    """Primitive defaults for string-like types that need valid placeholders."""

    def test_http_url_is_valid(self) -> None:
        val = _primitive_default("HttpUrl")
        TypeAdapter(HttpUrl).validate_python(val)

    def test_email_str_contains_at(self) -> None:
        val = _primitive_default("EmailStr")
        assert isinstance(val, str)
        assert "@" in val


class TestBaseRowUrlFields:
    """Base rows with URL-typed fields produce Pydantic-valid values."""

    def test_required_url_field_passes_validation(self) -> None:
        spec = spec_for_model(FeatureWithRequiredUrl)
        row = generate_base_row(spec)
        TypeAdapter(FeatureWithRequiredUrl).validate_python(row)


class TestGenerateBaseRow:
    def test_passes_pydantic_validation(self, connector_spec: ModelSpec) -> None:
        row = generate_base_row(connector_spec)
        assert connector_spec.source_type is not None
        TypeAdapter(connector_spec.source_type).validate_python(row)

    def test_required_fields_present(self, connector_spec: ModelSpec) -> None:
        row = generate_base_row(connector_spec)
        required_names = {f.name for f in connector_spec.fields if f.is_required}
        assert required_names <= set(row.keys())

    def test_optional_fields_absent(self, connector_spec: ModelSpec) -> None:
        row = generate_base_row(connector_spec)
        optional_names = {f.name for f in connector_spec.fields if not f.is_required}
        assert optional_names.isdisjoint(set(row.keys()))

    def test_id_is_deterministic_uuid(self, connector_spec: ModelSpec) -> None:
        row = generate_base_row(connector_spec)
        assert "id" in row
        parsed = uuid.UUID(row["id"])
        assert parsed.version == 5

    def test_geometry_is_valid_wkt(self, connector_spec: ModelSpec) -> None:
        row = generate_base_row(connector_spec)
        assert "geometry" in row
        assert row["geometry"].startswith("POINT")


class TestGenerateArmRows:
    def test_returns_dict_per_arm(
        self, segment_spec: ModelSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_arm_rows(segment_spec)
        assert segment_union.discriminator_mapping is not None
        assert set(rows.keys()) == set(segment_union.discriminator_mapping.keys())

    def test_each_row_passes_validation(
        self, segment_spec: ModelSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_arm_rows(segment_spec)
        adapter: TypeAdapter[object] = TypeAdapter(segment_union.source_annotation)
        for _arm_val, row in rows.items():
            adapter.validate_python(row)

    def test_discriminator_field_set(
        self, segment_spec: ModelSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_arm_rows(segment_spec)
        assert segment_union.discriminator_field is not None
        for arm_val, row in rows.items():
            assert row[segment_union.discriminator_field] == arm_val

    def test_arm_specific_required_fields_present(
        self, segment_spec: ModelSpec
    ) -> None:
        """Road arm requires 'class' field; water arm does not."""
        rows = generate_arm_rows(segment_spec)
        assert "class" in rows["road"]
        assert "class" not in rows["water"]


class TestPopulateOptionalFlag:
    """populate_optional flag controls recursion depth."""

    def test_value_for_field_default_skips_optional_children(
        self, connector_spec: ModelSpec
    ) -> None:
        """Default (`populate_optional=False`) yields sparse sub-models."""
        field = next(f for f in connector_spec.fields if f.name == "sources")
        model_ref = _list_of_model(field.shape)
        val = value_for_field(field, "Connector")
        assert isinstance(val, list)
        elem = val[0]
        assert isinstance(elem, dict)
        optional_names = {f.name for f in model_ref.model.fields if not f.is_required}
        assert not (optional_names & set(elem.keys()))

    def test_value_for_field_populate_includes_optional_children(
        self, connector_spec: ModelSpec
    ) -> None:
        """`populate_optional=True` yields sub-models that include optional fields."""
        field = next(f for f in connector_spec.fields if f.name == "sources")
        model_ref = _list_of_model(field.shape)
        val = value_for_field(field, "Connector", populate_optional=True)
        assert isinstance(val, list)
        elem = val[0]
        assert isinstance(elem, dict)
        optional_names = {f.name for f in model_ref.model.fields if not f.is_required}
        assert optional_names & set(elem.keys()) == optional_names


def _list_of_model(shape: object) -> ModelRef:
    """Peel `ArrayOf` / `NewTypeShape` layers to reach the inner `ModelRef`."""
    from overture.schema.codegen.extraction.field_walk import terminal_of

    terminal = terminal_of(shape)  # type: ignore[arg-type]
    assert isinstance(terminal, ModelRef), (
        f"Expected ModelRef terminal, got {type(terminal).__name__}"
    )
    return terminal


class TestGeneratePopulatedRow:
    def test_passes_pydantic_validation(self, connector_spec: ModelSpec) -> None:
        row = generate_populated_row(connector_spec)
        assert connector_spec.source_type is not None
        TypeAdapter(connector_spec.source_type).validate_python(row)

    def test_required_fields_present(self, connector_spec: ModelSpec) -> None:
        row = generate_populated_row(connector_spec)
        required_names = {f.name for f in connector_spec.fields if f.is_required}
        assert required_names <= set(row.keys())

    def test_optional_fields_present(self, connector_spec: ModelSpec) -> None:
        row = generate_populated_row(connector_spec)
        optional_names = {f.name for f in connector_spec.fields if not f.is_required}
        assert optional_names <= set(row.keys())

    def test_id_matches_sparse_row(self, connector_spec: ModelSpec) -> None:
        sparse = generate_base_row(connector_spec)
        populated = generate_populated_row(connector_spec)
        assert populated["id"] == sparse["id"]

    def test_nested_structs_populated(self, connector_spec: ModelSpec) -> None:
        """Optional struct fields contain populated sub-dicts, not empty."""
        row = generate_populated_row(connector_spec)
        assert "sources" in row
        elem = row["sources"][0]
        sources_field = next(f for f in connector_spec.fields if f.name == "sources")
        model_ref = _list_of_model(sources_field.shape)
        optional_source_fields = {
            f.name for f in model_ref.model.fields if not f.is_required
        }
        present = optional_source_fields & set(elem.keys())
        assert present == optional_source_fields


class TestGeneratePopulatedArmRows:
    def test_returns_dict_per_arm(
        self, segment_spec: ModelSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_populated_arm_rows(segment_spec)
        assert segment_union.discriminator_mapping is not None
        assert set(rows.keys()) == set(segment_union.discriminator_mapping.keys())

    def test_each_row_passes_validation(
        self, segment_spec: ModelSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_populated_arm_rows(segment_spec)
        adapter: TypeAdapter[object] = TypeAdapter(segment_union.source_annotation)
        for _arm_val, row in rows.items():
            adapter.validate_python(row)

    def test_discriminator_field_set(
        self, segment_spec: ModelSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_populated_arm_rows(segment_spec)
        assert segment_union.discriminator_field is not None
        for arm_val, row in rows.items():
            assert row[segment_union.discriminator_field] == arm_val

    def test_optional_fields_present(self, segment_spec: ModelSpec) -> None:
        """Populated arm rows include optional fields."""
        rows = generate_populated_arm_rows(segment_spec)
        # Road arm has optional speed_limits
        road_row = rows["road"]
        assert "speed_limits" in road_row


class TestMapFieldPopulation:
    """MapOf fields are populated with a constraint-valid entry, not `{}`.

    An empty map satisfies Pydantic but leaves nothing for a conformance
    scenario to corrupt, so the generated key/value checks would never
    fire. The entry's key and value must satisfy their own constraints
    (`dict[LanguageTag, StrippedString]` -> key `"en"`, value `"clean"`).
    """

    def test_required_map_field_is_populated(self) -> None:
        spec = spec_for_model(FeatureWithDict)
        row = generate_base_row(spec)
        # metadata: dict[str, int] is required.
        assert row["metadata"], "required map field generated as empty dict"
        ((k, v),) = row["metadata"].items()
        assert isinstance(k, str)
        assert isinstance(v, int)

    def test_constrained_map_entry_is_valid(self) -> None:
        spec = spec_for_model(FeatureWithDict)
        row = generate_populated_row(spec)
        assert row["names"], "constrained map field generated as empty dict"
        ((key, value),) = row["names"].items()
        assert key == "en"  # LanguageTagConstraint.valid
        assert value == "clean"  # StrippedConstraint.valid

    def test_populated_row_passes_pydantic(self) -> None:
        spec = spec_for_model(FeatureWithDict)
        row = generate_populated_row(spec)
        TypeAdapter(FeatureWithDict).validate_python(row)

    def test_any_valued_map_generates_empty(self) -> None:
        # `dict[str, Any]` (e.g. Infrastructure.source_tags) has no value
        # constraint -- hence no value check -- and `Any` has no value
        # strategy, so the map stays empty rather than crashing.
        from typing import Any

        from overture.schema.codegen.extraction.model_extraction import extract_model
        from pydantic import BaseModel

        class TagsModel(BaseModel):
            source_tags: dict[str, Any] | None = None

        spec = extract_model(TagsModel)
        row = generate_populated_row(spec)
        assert row.get("source_tags") == {}


class TestRawPatternFailsLoud:
    """An uncurated raw `Field(pattern=)` fails loud during base-row generation.

    Symmetric with `invalid_value`: both sides point at the missing
    `PATTERN_VALUES` entry. Generating a valid value for a pattern with no
    curated entry raises an actionable error that names the gap, rather than
    yielding a value that fails the pattern and surfaces downstream as a
    misleading "row should be valid" Pydantic error.
    """

    _DUMMY_SCALAR = Primitive(base_type="str")
    _DUMMY_CS = ConstraintSource(source_ref=None, source_name=None, constraint=object())

    def test_curated_pattern_returns_valid(self) -> None:
        # Sources.license_priority key pattern, anchor-normalized.
        desc = ExpressionDescriptor(
            function="check_pattern", args=(r"^[A-Za-z0-9._+\-]+\z",)
        )
        assert (
            _value_from_check_pattern(desc, self._DUMMY_SCALAR, self._DUMMY_CS)
            == "ODbL-1.0"
        )

    def test_uncurated_pattern_raises(self) -> None:
        desc = ExpressionDescriptor(function="check_pattern", args=(r"^xyz\z",))
        with pytest.raises(ValueError, match="check_pattern"):
            _value_from_check_pattern(desc, self._DUMMY_SCALAR, self._DUMMY_CS)

    def test_uncurated_pattern_field_raises_during_generation(self) -> None:
        # End to end: a scalar field carrying an uncurated raw pattern raises
        # the actionable error at base-row generation, not as a downstream
        # Pydantic "row should be valid" failure.
        (meta,) = Field(pattern=r"^[0-9]{4}$").metadata
        field = FieldSpec(
            name="code",
            shape=Primitive(
                base_type="str",
                constraints=(
                    ConstraintSource(
                        source_ref=None, source_name=None, constraint=meta
                    ),
                ),
            ),
        )
        with pytest.raises(ValueError, match="check_pattern"):
            value_for_field(field, "Foo")


class TestValueForShapeScalarVariants:
    """_value_for_shape handles the Scalar variants it can reach."""

    def test_any_scalar_raises(self) -> None:
        # No schema declares a `dict[K, Any]` value, so `AnyScalar` has no
        # value strategy; reaching it raises rather than guessing.
        field = FieldSpec(name="x", shape=AnyScalar())
        with pytest.raises(TypeError, match="AnyScalar reached base-row generation"):
            value_for_field(field, "Foo")

    def test_literal_scalar_returns_first_value(self) -> None:
        field = FieldSpec(name="x", shape=LiteralScalar(values=("road",)))
        assert value_for_field(field, "Foo") == "road"


class TestMinFieldsSetSatisfied:
    """`_satisfy_model_constraints` populates optional fields for `min_fields_set`."""

    def test_min_fields_set_populates_optional_fields(self) -> None:
        from overture.schema.codegen.extraction.model_extraction import extract_model
        from overture.schema.system.model_constraint import min_fields_set
        from pydantic import BaseModel

        @min_fields_set(2)
        class MinTwoModel(BaseModel):
            a: str | None = None
            b: str | None = None
            c: str | None = None

        spec = extract_model(MinTwoModel)
        row = generate_base_row(spec)
        present = [name for name in ("a", "b", "c") if name in row]
        assert len(present) >= 2

    def test_min_fields_set_counts_required_fields(self) -> None:
        # Required fields are always present in the sparse base row, and they
        # count against `min_fields_set(N)` -- matching Pydantic's
        # `model_fields_set` semantics. With one required + three optional
        # and `min_fields_set(2)`, the required field plus one optional
        # already satisfy the constraint, so the sparse row only needs
        # one additional optional fill.
        from overture.schema.codegen.extraction.model_extraction import extract_model
        from overture.schema.system.model_constraint import min_fields_set
        from pydantic import BaseModel

        @min_fields_set(2)
        class MixedMinModel(BaseModel):
            required_field: str
            opt_a: str | None = None
            opt_b: str | None = None
            opt_c: str | None = None

        spec = extract_model(MixedMinModel)
        row = generate_base_row(spec)
        assert "required_field" in row
        present_optional = [n for n in ("opt_a", "opt_b", "opt_c") if n in row]
        assert len(present_optional) >= 1
        assert (
            sum(
                1
                for name in row
                if name in {"required_field", "opt_a", "opt_b", "opt_c"}
            )
            >= 2
        )

    def test_min_fields_set_all_required_needs_no_optional_fill(self) -> None:
        # When required fields alone satisfy `count`, no optional fills are
        # needed -- matching Pydantic, which counts required fields toward
        # `model_fields_set`.
        from overture.schema.codegen.extraction.model_extraction import extract_model
        from overture.schema.system.model_constraint import min_fields_set
        from pydantic import BaseModel

        @min_fields_set(2)
        class AllRequiredModel(BaseModel):
            req_a: str
            req_b: str
            opt_a: str | None = None

        spec = extract_model(AllRequiredModel)
        row = generate_base_row(spec)
        assert "req_a" in row and "req_b" in row
        assert "opt_a" not in row


class _ModeColor(str, Enum):
    RED = "red"
    BLUE = "blue"


@require_if(["extra"], ~FieldEqCondition("mode", _ModeColor.BLUE))
class _ModeModelRequireIf(BaseModel):
    mode: _ModeColor = _ModeColor.BLUE
    extra: str | None = None


@forbid_if(["extra"], ~FieldEqCondition("mode", _ModeColor.BLUE))
class _ModeModelForbidIf(BaseModel):
    mode: _ModeColor = _ModeColor.BLUE
    extra: str | None = None


# Default mode=RED means Not(mode == BLUE) is True from the start, so
# generate_base_row must fill 'extra' without any manual row mutation.
@require_if(["extra"], ~FieldEqCondition("mode", _ModeColor.BLUE))
class _ModeModelRequireIfTriggered(BaseModel):
    mode: _ModeColor = _ModeColor.RED
    extra: str | None = None


class TestNotConditionBaseRow:
    """Base-row generation handles Not(FieldEqCondition) in require_if/forbid_if."""

    def test_require_if_not_condition_fills_field(self) -> None:
        """generate_base_row fills the require_if target when Not-condition holds.

        _ModeModelRequireIfTriggered defaults mode=RED, so Not(mode == BLUE) is
        True from the start. generate_base_row must fill 'extra' end-to-end
        without any manual row mutation.
        """
        spec = extract_model(_ModeModelRequireIfTriggered)
        row = generate_base_row(spec)
        # 'mode' has a default (RED) and may be omitted from the sparse row;
        # what matters is that the Not-condition was evaluated and 'extra' filled.
        assert "extra" in row
        assert row["extra"] is not None
        TypeAdapter(_ModeModelRequireIfTriggered).validate_python(row)

    def test_forbid_if_not_condition_removes_field(self) -> None:
        """forbid_if triggered by Not(FieldEqCondition) removes the forbidden field."""
        from overture.schema.codegen.pyspark.test_data.base_row import (
            _satisfy_model_constraints,
        )

        spec = extract_model(_ModeModelForbidIf)
        row: dict[str, object] = {
            "mode": _ModeColor.RED.value,
            "extra": "should be removed",
        }
        _satisfy_model_constraints(row, spec)
        # With mode='red', Not(mode == BLUE) is True -> extra must be absent
        assert "extra" not in row

    def test_unknown_condition_type_raises(self) -> None:
        """_row_satisfies_condition must raise for unknown condition kinds."""
        from overture.schema.codegen.pyspark.test_data.base_row import (
            _row_satisfies_condition,
        )

        class _Unknown:
            pass

        with pytest.raises((TypeError, NotImplementedError)):
            _row_satisfies_condition({}, _Unknown())

    def test_not_field_eq_condition_base_row_passes_pydantic(self) -> None:
        """A model with Not(FieldEqCondition) conditions produces a valid base row."""
        spec = extract_model(_ModeModelRequireIf)
        row = generate_base_row(spec)
        TypeAdapter(_ModeModelRequireIf).validate_python(row)


class TestMultiBoundScalarConstraints:
    """_value_from_scalar_constraints merges multiple check_bounds before calling valid_bound."""

    def test_gt_and_lt_float_tight_interval_returns_interior_value(self) -> None:
        """Synthesized value satisfies both Gt(0.0) and Lt(1.0) simultaneously."""
        # float bounds: Gt(0.0)+Lt(1.0): gt+1 = 1.0 violates lt=1.0 (boundary)
        scalar = Primitive(
            base_type="float64",
            constraints=(
                ConstraintSource(source_ref=None, source_name=None, constraint=Gt(0.0)),
                ConstraintSource(source_ref=None, source_name=None, constraint=Lt(1.0)),
            ),
        )
        result = _value_from_scalar_constraints(scalar)
        assert isinstance(result, float)
        assert 0.0 < result < 1.0
