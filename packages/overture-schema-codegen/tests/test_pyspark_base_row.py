"""Tests for valid-row generation from FeatureSpecs."""

import uuid

import pytest
from codegen_test_support import (
    FeatureWithRequiredUrl,
    discover_feature,
    feature_spec_for_model,
)
from overture.schema.codegen.extraction.field import AnyScalar, LiteralScalar, ModelRef
from overture.schema.codegen.extraction.specs import (
    FeatureSpec,
    FieldSpec,
    UnionSpec,
)
from overture.schema.codegen.pyspark.test_data.base_row import (
    _primitive_default,
    generate_arm_rows,
    generate_base_row,
    generate_populated_arm_rows,
    generate_populated_row,
    value_for_field,
)
from pydantic import HttpUrl, TypeAdapter


@pytest.fixture(scope="module")
def connector_spec() -> FeatureSpec:
    return discover_feature("Connector")


@pytest.fixture(scope="module")
def segment_spec() -> FeatureSpec:
    return discover_feature("Segment")


@pytest.fixture(scope="module")
def segment_union(segment_spec: FeatureSpec) -> UnionSpec:
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
        spec = feature_spec_for_model(FeatureWithRequiredUrl)
        row = generate_base_row(spec)
        TypeAdapter(FeatureWithRequiredUrl).validate_python(row)


class TestGenerateBaseRow:
    def test_passes_pydantic_validation(self, connector_spec: FeatureSpec) -> None:
        row = generate_base_row(connector_spec)
        assert connector_spec.source_type is not None
        TypeAdapter(connector_spec.source_type).validate_python(row)

    def test_required_fields_present(self, connector_spec: FeatureSpec) -> None:
        row = generate_base_row(connector_spec)
        required_names = {f.name for f in connector_spec.fields if f.is_required}
        assert required_names <= set(row.keys())

    def test_optional_fields_absent(self, connector_spec: FeatureSpec) -> None:
        row = generate_base_row(connector_spec)
        optional_names = {f.name for f in connector_spec.fields if not f.is_required}
        assert optional_names.isdisjoint(set(row.keys()))

    def test_id_is_deterministic_uuid(self, connector_spec: FeatureSpec) -> None:
        row = generate_base_row(connector_spec)
        assert "id" in row
        parsed = uuid.UUID(row["id"])
        assert parsed.version == 5

    def test_geometry_is_valid_wkt(self, connector_spec: FeatureSpec) -> None:
        row = generate_base_row(connector_spec)
        assert "geometry" in row
        assert row["geometry"].startswith("POINT")


class TestGenerateArmRows:
    def test_returns_dict_per_arm(
        self, segment_spec: FeatureSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_arm_rows(segment_spec)
        assert segment_union.discriminator_mapping is not None
        assert set(rows.keys()) == set(segment_union.discriminator_mapping.keys())

    def test_each_row_passes_validation(
        self, segment_spec: FeatureSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_arm_rows(segment_spec)
        adapter: TypeAdapter[object] = TypeAdapter(segment_union.source_annotation)
        for _arm_val, row in rows.items():
            adapter.validate_python(row)

    def test_discriminator_field_set(
        self, segment_spec: FeatureSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_arm_rows(segment_spec)
        assert segment_union.discriminator_field is not None
        for arm_val, row in rows.items():
            assert row[segment_union.discriminator_field] == arm_val

    def test_arm_specific_required_fields_present(
        self, segment_spec: FeatureSpec
    ) -> None:
        """Road arm requires 'class' field; water arm does not."""
        rows = generate_arm_rows(segment_spec)
        assert "class" in rows["road"]
        assert "class" not in rows["water"]


class TestPopulateOptionalFlag:
    """populate_optional flag controls recursion depth."""

    def test_value_for_field_default_skips_optional_children(
        self, connector_spec: FeatureSpec
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
        self, connector_spec: FeatureSpec
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
    def test_passes_pydantic_validation(self, connector_spec: FeatureSpec) -> None:
        row = generate_populated_row(connector_spec)
        assert connector_spec.source_type is not None
        TypeAdapter(connector_spec.source_type).validate_python(row)

    def test_required_fields_present(self, connector_spec: FeatureSpec) -> None:
        row = generate_populated_row(connector_spec)
        required_names = {f.name for f in connector_spec.fields if f.is_required}
        assert required_names <= set(row.keys())

    def test_optional_fields_present(self, connector_spec: FeatureSpec) -> None:
        row = generate_populated_row(connector_spec)
        optional_names = {f.name for f in connector_spec.fields if not f.is_required}
        assert optional_names <= set(row.keys())

    def test_id_matches_sparse_row(self, connector_spec: FeatureSpec) -> None:
        sparse = generate_base_row(connector_spec)
        populated = generate_populated_row(connector_spec)
        assert populated["id"] == sparse["id"]

    def test_nested_structs_populated(self, connector_spec: FeatureSpec) -> None:
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
        self, segment_spec: FeatureSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_populated_arm_rows(segment_spec)
        assert segment_union.discriminator_mapping is not None
        assert set(rows.keys()) == set(segment_union.discriminator_mapping.keys())

    def test_each_row_passes_validation(
        self, segment_spec: FeatureSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_populated_arm_rows(segment_spec)
        adapter: TypeAdapter[object] = TypeAdapter(segment_union.source_annotation)
        for _arm_val, row in rows.items():
            adapter.validate_python(row)

    def test_discriminator_field_set(
        self, segment_spec: FeatureSpec, segment_union: UnionSpec
    ) -> None:
        rows = generate_populated_arm_rows(segment_spec)
        assert segment_union.discriminator_field is not None
        for arm_val, row in rows.items():
            assert row[segment_union.discriminator_field] == arm_val

    def test_optional_fields_present(self, segment_spec: FeatureSpec) -> None:
        """Populated arm rows include optional fields."""
        rows = generate_populated_arm_rows(segment_spec)
        # Road arm has optional speed_limits
        road_row = rows["road"]
        assert "speed_limits" in road_row


class TestValueForShapeScalarVariants:
    """_value_for_shape handles the Scalar variants it can reach."""

    def test_any_scalar_raises(self) -> None:
        # `AnyScalar` only appears as a `MapOf` value type in feature
        # models; `_value_for_shape` returns `{}` for `MapOf` without
        # descending, so reaching `AnyScalar` directly is a bug.
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
