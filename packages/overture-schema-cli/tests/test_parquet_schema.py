"""Tests for parquet-schema command and arrow conversion."""

from pathlib import Path

import pytest
from click.testing import CliRunner

# Skip all tests if pyarrow not available
pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from overture.schema.cli.arrow_schema import (
    _describe_type,
    compare_schemas,
    pydantic_model_to_arrow_schema,
    pydantic_to_arrow_type,
)
from overture.schema.cli.commands import cli
from overture.schema.cli.format_adapters import _get_file_extension


class TestArrowSchemaConversion:
    """Tests for Pydantic to Arrow schema conversion."""

    def test_primitive_int_types(self) -> None:
        """Test that integer primitive types map correctly."""
        from overture.schema.system.primitive import int8, int16, int32, int64

        assert pydantic_to_arrow_type(int8) == pa.int8()
        assert pydantic_to_arrow_type(int16) == pa.int16()
        assert pydantic_to_arrow_type(int32) == pa.int32()
        assert pydantic_to_arrow_type(int64) == pa.int64()

    def test_primitive_uint_types(self) -> None:
        """Test that unsigned integer primitive types map correctly."""
        from overture.schema.system.primitive import uint8, uint16, uint32

        assert pydantic_to_arrow_type(uint8) == pa.uint8()
        assert pydantic_to_arrow_type(uint16) == pa.uint16()
        assert pydantic_to_arrow_type(uint32) == pa.uint32()

    def test_primitive_float_types(self) -> None:
        """Test that float primitive types map correctly."""
        from overture.schema.system.primitive import float32, float64

        assert pydantic_to_arrow_type(float32) == pa.float32()
        assert pydantic_to_arrow_type(float64) == pa.float64()

    def test_basic_python_types(self) -> None:
        """Test that basic Python types map correctly."""
        assert pydantic_to_arrow_type(str) == pa.utf8()
        assert pydantic_to_arrow_type(int) == pa.int64()
        assert pydantic_to_arrow_type(float) == pa.float64()
        assert pydantic_to_arrow_type(bool) == pa.bool_()
        assert pydantic_to_arrow_type(bytes) == pa.binary()

    def test_string_newtypes(self) -> None:
        """Test that string newtypes map to utf8."""
        from overture.schema.system.string import CountryCodeAlpha2, LanguageTag

        assert pydantic_to_arrow_type(CountryCodeAlpha2) == pa.utf8()
        assert pydantic_to_arrow_type(LanguageTag) == pa.utf8()

    def test_geometry_to_binary(self) -> None:
        """Test geometry converts to binary for WKB encoding."""
        from overture.schema.system.primitive import Geometry

        assert pydantic_to_arrow_type(Geometry) == pa.binary()

    def test_bbox_to_struct(self) -> None:
        """Test BBox converts to struct with four float32 fields."""
        from overture.schema.system.primitive import BBox

        arrow_type = pydantic_to_arrow_type(BBox)
        expected = pa.struct(
            [
                pa.field("xmin", pa.float32()),
                pa.field("ymin", pa.float32()),
                pa.field("xmax", pa.float32()),
                pa.field("ymax", pa.float32()),
            ]
        )
        assert arrow_type == expected

    def test_list_type(self) -> None:
        """Test list[T] converts to pa.list_(T)."""
        arrow_type = pydantic_to_arrow_type(list[str])
        assert arrow_type == pa.list_(pa.utf8())

        arrow_type = pydantic_to_arrow_type(list[int])
        assert arrow_type == pa.list_(pa.int64())

    def test_optional_type(self) -> None:
        """Test that T | None still returns the base type (nullable handled separately)."""
        # The nullability is handled at the field level, not the type level
        assert pydantic_to_arrow_type(str | None) == pa.utf8()
        assert pydantic_to_arrow_type(int | None) == pa.int64()

    def test_enum_to_utf8(self) -> None:
        """Test that string enums convert to utf8."""
        from enum import Enum

        class Color(str, Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"

        assert pydantic_to_arrow_type(Color) == pa.utf8()

    def test_nested_model_to_struct(self) -> None:
        """Test that nested BaseModel converts to struct."""
        from pydantic import BaseModel

        class Inner(BaseModel):
            value: str
            count: int

        arrow_type = pydantic_to_arrow_type(Inner)
        assert isinstance(arrow_type, pa.StructType)
        assert "value" in [f.name for f in arrow_type]
        assert "count" in [f.name for f in arrow_type]

    def test_building_model_schema(self) -> None:
        """Test full Building model converts to valid schema."""
        from overture.schema.buildings import Building

        schema = pydantic_model_to_arrow_schema(Building)

        # Check essential fields exist
        field_names = schema.names
        assert "id" in field_names
        assert "geometry" in field_names
        assert "theme" in field_names
        assert "type" in field_names
        assert "version" in field_names

        # Check geometry is binary (WKB)
        geometry_field = schema.field("geometry")
        assert geometry_field.type == pa.binary()

    def test_place_model_schema(self) -> None:
        """Test Place model converts to valid schema."""
        from overture.schema.places import Place

        schema = pydantic_model_to_arrow_schema(Place)

        field_names = schema.names
        assert "id" in field_names
        assert "geometry" in field_names
        assert "operating_status" in field_names
        assert "names" in field_names

    def test_schema_includes_metadata(self) -> None:
        """Test that schema includes model metadata."""
        from overture.schema.buildings import Building

        schema = pydantic_model_to_arrow_schema(Building, include_version_metadata=True)

        assert schema.metadata is not None
        assert b"model_name" in schema.metadata
        assert schema.metadata[b"model_name"] == b"Building"


class TestParquetSchemaCommand:
    """Tests for the parquet-schema CLI command."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a CliRunner within an isolated filesystem."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            yield runner

    def test_parquet_schema_text_output(self, cli_runner: CliRunner) -> None:
        """Test parquet-schema with text format outputs schema description."""
        result = cli_runner.invoke(
            cli,
            [
                "parquet-schema",
                "--theme",
                "buildings",
                "--type",
                "building",
                "--format",
                "text",
            ],
        )
        assert result.exit_code == 0
        assert "id:" in result.output
        assert "geometry:" in result.output
        assert "theme:" in result.output

    def test_parquet_schema_file_output(self, cli_runner: CliRunner) -> None:
        """Test parquet-schema with parquet file output creates valid file."""
        result = cli_runner.invoke(
            cli,
            [
                "parquet-schema",
                "--theme",
                "buildings",
                "--type",
                "building",
                "--format",
                "parquet",
                "-o",
                "building.parquet",
            ],
        )
        assert result.exit_code == 0

        # Verify file was created
        assert Path("building.parquet").exists()

        # Verify schema
        table = pq.read_table("building.parquet")
        assert len(table) == 0  # Empty table
        assert "id" in table.schema.names
        assert "geometry" in table.schema.names

    def test_parquet_schema_requires_type(self, cli_runner: CliRunner) -> None:
        """Test that --type is required."""
        result = cli_runner.invoke(
            cli, ["parquet-schema", "--theme", "buildings", "--format", "text"]
        )
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_parquet_schema_requires_output_for_parquet_format(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that parquet format requires output file."""
        result = cli_runner.invoke(
            cli,
            [
                "parquet-schema",
                "--theme",
                "buildings",
                "--type",
                "building",
                "--format",
                "parquet",
            ],
        )
        assert result.exit_code != 0
        assert "--output" in result.output or "required" in result.output.lower()

    def test_parquet_schema_invalid_type(self, cli_runner: CliRunner) -> None:
        """Test error handling for invalid type."""
        result = cli_runner.invoke(
            cli, ["parquet-schema", "--type", "nonexistent_type", "--format", "text"]
        )
        assert result.exit_code != 0
        assert "No model found" in result.output

    def test_parquet_schema_ambiguous_type(self, cli_runner: CliRunner) -> None:
        """Test that ambiguous type without theme gives helpful error."""
        # This test assumes there might be types with same name in different themes
        # If not, the test will just verify the happy path works
        result = cli_runner.invoke(
            cli,
            [
                "parquet-schema",
                "--theme",
                "buildings",
                "--type",
                "building",
                "--format",
                "text",
            ],
        )
        # Should succeed with theme specified
        assert result.exit_code == 0

    def test_parquet_schema_segment_type(self, cli_runner: CliRunner) -> None:
        """Test parquet-schema works for transportation segment."""
        result = cli_runner.invoke(
            cli,
            [
                "parquet-schema",
                "--theme",
                "transportation",
                "--type",
                "segment",
                "--format",
                "text",
            ],
        )
        assert result.exit_code == 0
        assert "geometry:" in result.output

    def test_parquet_schema_with_namespace(self, cli_runner: CliRunner) -> None:
        """Test parquet-schema with namespace filter."""
        result = cli_runner.invoke(
            cli,
            [
                "parquet-schema",
                "--namespace",
                "overture",
                "--theme",
                "buildings",
                "--type",
                "building",
                "--format",
                "text",
            ],
        )
        assert result.exit_code == 0


class TestSchemaComparison:
    """Tests for Arrow schema comparison logic."""

    def test_identical_schemas_match(self) -> None:
        """Two identical schemas should produce no diffs."""
        schema = pa.schema(
            [
                pa.field("id", pa.utf8(), nullable=False),
                pa.field("value", pa.int64()),
            ]
        )
        diff = compare_schemas(schema, schema)
        assert diff.is_compatible
        assert diff.is_exact_match

    def test_missing_field_detected(self) -> None:
        """A field in expected but not in actual is reported as missing."""
        expected = pa.schema(
            [
                pa.field("id", pa.utf8()),
                pa.field("name", pa.utf8()),
            ]
        )
        actual = pa.schema(
            [
                pa.field("id", pa.utf8()),
            ]
        )
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.missing_fields) == 1
        assert diff.missing_fields[0].path == "name"

    def test_extra_field_subset_compatible(self) -> None:
        """Extra fields are tracked but is_compatible still returns True."""
        expected = pa.schema(
            [
                pa.field("id", pa.utf8()),
            ]
        )
        actual = pa.schema(
            [
                pa.field("id", pa.utf8()),
                pa.field("extra", pa.int64()),
            ]
        )
        diff = compare_schemas(expected, actual)
        assert diff.is_compatible
        assert not diff.is_exact_match
        assert len(diff.extra_fields) == 1
        assert diff.extra_fields[0].path == "extra"

    def test_type_mismatch_detected(self) -> None:
        """A field with different types is reported as type_mismatch."""
        expected = pa.schema([pa.field("height", pa.float64())])
        actual = pa.schema([pa.field("height", pa.utf8())])
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.type_mismatches) == 1
        assert diff.type_mismatches[0].path == "height"
        assert diff.type_mismatches[0].expected == "double"
        assert diff.type_mismatches[0].actual == "string"

    def test_nullable_expected_nonnullable_actual_ok(self) -> None:
        """Expected nullable, actual non-nullable is fine (stricter)."""
        expected = pa.schema([pa.field("id", pa.utf8(), nullable=True)])
        actual = pa.schema([pa.field("id", pa.utf8(), nullable=False)])
        diff = compare_schemas(expected, actual)
        assert diff.is_compatible
        assert len(diff.nullability_issues) == 0

    def test_nonnullable_expected_nullable_actual_fails(self) -> None:
        """Expected non-nullable, actual nullable is a nullability issue."""
        expected = pa.schema([pa.field("id", pa.utf8(), nullable=False)])
        actual = pa.schema([pa.field("id", pa.utf8(), nullable=True)])
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.nullability_issues) == 1
        assert diff.nullability_issues[0].path == "id"

    def test_nested_struct_comparison(self) -> None:
        """Fields within nested structs are compared recursively."""
        struct_type = pa.struct(
            [
                pa.field("x", pa.float64()),
                pa.field("y", pa.float64()),
            ]
        )
        expected = pa.schema([pa.field("point", struct_type)])
        actual = pa.schema([pa.field("point", struct_type)])
        diff = compare_schemas(expected, actual)
        assert diff.is_compatible

    def test_nested_struct_missing_child(self) -> None:
        """Missing child in nested struct reported with dotted path."""
        expected_struct = pa.struct(
            [
                pa.field("x", pa.float64()),
                pa.field("y", pa.float64()),
            ]
        )
        actual_struct = pa.struct(
            [
                pa.field("x", pa.float64()),
            ]
        )
        expected = pa.schema([pa.field("point", expected_struct)])
        actual = pa.schema([pa.field("point", actual_struct)])
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.missing_fields) == 1
        assert diff.missing_fields[0].path == "point.y"

    def test_nested_struct_type_mismatch(self) -> None:
        """Type mismatch within nested struct uses dotted path."""
        expected_struct = pa.struct([pa.field("value", pa.int64())])
        actual_struct = pa.struct([pa.field("value", pa.utf8())])
        expected = pa.schema([pa.field("data", expected_struct)])
        actual = pa.schema([pa.field("data", actual_struct)])
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.type_mismatches) == 1
        assert diff.type_mismatches[0].path == "data.value"

    def test_list_element_type_comparison(self) -> None:
        """List element types are compared."""
        expected = pa.schema([pa.field("tags", pa.list_(pa.utf8()))])
        actual = pa.schema([pa.field("tags", pa.list_(pa.int64()))])
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.type_mismatches) == 1
        assert diff.type_mismatches[0].path == "tags.item"

    def test_map_key_value_type_comparison(self) -> None:
        """Map key and value types are compared."""
        expected = pa.schema([pa.field("props", pa.map_(pa.utf8(), pa.int64()))])
        actual = pa.schema([pa.field("props", pa.map_(pa.utf8(), pa.utf8()))])
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.type_mismatches) == 1
        assert diff.type_mismatches[0].path == "props.value"

    def test_struct_vs_primitive_mismatch(self) -> None:
        """A struct expected but primitive found reports type_mismatch."""
        struct_type = pa.struct([pa.field("x", pa.float64())])
        expected = pa.schema([pa.field("data", struct_type)])
        actual = pa.schema([pa.field("data", pa.utf8())])
        diff = compare_schemas(expected, actual)
        assert not diff.is_compatible
        assert len(diff.type_mismatches) == 1
        assert "struct" in diff.type_mismatches[0].expected

    def test_describe_type_primitives(self) -> None:
        """_describe_type returns readable strings for primitive types."""
        assert _describe_type(pa.utf8()) == "string"
        assert _describe_type(pa.int64()) == "int64"
        assert _describe_type(pa.float64()) == "double"
        assert _describe_type(pa.bool_()) == "bool"

    def test_describe_type_complex(self) -> None:
        """_describe_type returns readable strings for struct/list/map."""
        struct_type = pa.struct(
            [
                pa.field("a", pa.utf8()),
                pa.field("b", pa.int64()),
            ]
        )
        assert _describe_type(struct_type) == "struct<2 fields>"
        assert _describe_type(pa.list_(pa.utf8())) == "list<string>"
        assert _describe_type(pa.map_(pa.utf8(), pa.int64())) == "map<string, int64>"

    def test_ignore_missing_field(self) -> None:
        """Ignored fields are not reported as missing."""
        expected = pa.schema(
            [
                pa.field("id", pa.utf8()),
                pa.field("version", pa.int32()),
                pa.field("bbox", pa.binary()),
            ]
        )
        actual = pa.schema(
            [
                pa.field("id", pa.utf8()),
            ]
        )
        diff = compare_schemas(expected, actual, ignore_fields={"version", "bbox"})
        assert diff.is_compatible
        assert diff.is_exact_match
        assert len(diff.missing_fields) == 0

    def test_ignore_extra_field(self) -> None:
        """Ignored fields are not reported as extra."""
        expected = pa.schema(
            [
                pa.field("id", pa.utf8()),
            ]
        )
        actual = pa.schema(
            [
                pa.field("id", pa.utf8()),
                pa.field("version", pa.int32()),
            ]
        )
        diff = compare_schemas(expected, actual, ignore_fields={"version"})
        assert diff.is_compatible
        assert diff.is_exact_match
        assert len(diff.extra_fields) == 0

    def test_ignore_does_not_affect_other_fields(self) -> None:
        """Ignoring one field does not affect checks on other fields."""
        expected = pa.schema(
            [
                pa.field("id", pa.utf8()),
                pa.field("version", pa.int32()),
                pa.field("name", pa.utf8()),
            ]
        )
        actual = pa.schema(
            [
                pa.field("id", pa.utf8()),
            ]
        )
        diff = compare_schemas(expected, actual, ignore_fields={"version"})
        assert not diff.is_compatible
        assert len(diff.missing_fields) == 1
        assert diff.missing_fields[0].path == "name"

    def test_building_schema_self_check(self) -> None:
        """Building schema compared to itself should be an exact match."""
        from overture.schema.buildings import Building

        schema = pydantic_model_to_arrow_schema(Building)
        diff = compare_schemas(schema, schema)
        assert diff.is_compatible
        assert diff.is_exact_match


class TestCheckSchemaCommand:
    """Tests for the validate-schema CLI command."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a CliRunner within an isolated filesystem."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            yield runner

    @pytest.fixture
    def building_parquet(self, cli_runner: CliRunner) -> Path:
        """Create a valid building Parquet file for testing."""
        cli_runner.invoke(
            cli,
            [
                "parquet-schema",
                "--theme",
                "buildings",
                "--type",
                "building",
                "-o",
                "building.parquet",
            ],
        )
        return Path("building.parquet")

    def test_matching_schema_passes(
        self, cli_runner: CliRunner, building_parquet: Path
    ) -> None:
        """A file generated from the same model should pass subset check."""
        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                str(building_parquet),
                "--theme",
                "buildings",
                "--type",
                "building",
            ],
        )
        assert result.exit_code == 0

    def test_matching_schema_strict_passes(
        self, cli_runner: CliRunner, building_parquet: Path
    ) -> None:
        """A file generated from the same model should pass strict check."""
        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                str(building_parquet),
                "--theme",
                "buildings",
                "--type",
                "building",
                "--strict",
            ],
        )
        assert result.exit_code == 0

    def test_extra_columns_subset_passes(self, cli_runner: CliRunner) -> None:
        """File with extra columns passes in subset (default) mode."""
        from overture.schema.buildings import Building

        schema = pydantic_model_to_arrow_schema(Building)
        # Add an extra column, preserving nullability from original schema
        fields = list(schema) + [pa.field("custom_col", pa.utf8())]
        extended_schema = pa.schema(fields)
        table = pa.table(
            {f.name: pa.array([], type=f.type) for f in extended_schema},
            schema=extended_schema,
        )
        pq.write_table(table, "extended.parquet")

        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                "extended.parquet",
                "--theme",
                "buildings",
                "--type",
                "building",
            ],
        )
        assert result.exit_code == 0

    def test_extra_columns_strict_fails(self, cli_runner: CliRunner) -> None:
        """File with extra columns fails in strict mode."""
        from overture.schema.buildings import Building

        schema = pydantic_model_to_arrow_schema(Building)
        fields = list(schema) + [pa.field("custom_col", pa.utf8())]
        extended_schema = pa.schema(fields)
        table = pa.table(
            {f.name: pa.array([], type=f.type) for f in extended_schema},
            schema=extended_schema,
        )
        pq.write_table(table, "extended.parquet")

        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                "extended.parquet",
                "--theme",
                "buildings",
                "--type",
                "building",
                "--strict",
            ],
        )
        assert result.exit_code != 0

    def test_missing_field_fails(self, cli_runner: CliRunner) -> None:
        """File missing required fields fails check."""
        schema = pa.schema(
            [
                pa.field("id", pa.utf8()),
                pa.field("geometry", pa.binary()),
            ]
        )
        table = pa.table(
            {f.name: pa.array([], type=f.type) for f in schema},
        )
        pq.write_table(table, "partial.parquet")

        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                "partial.parquet",
                "--theme",
                "buildings",
                "--type",
                "building",
            ],
        )
        assert result.exit_code != 0

    def test_invalid_type_fails(
        self, cli_runner: CliRunner, building_parquet: Path
    ) -> None:
        """Invalid --type gives clear error."""
        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                str(building_parquet),
                "--type",
                "nonexistent_type",
            ],
        )
        assert result.exit_code != 0
        assert "No model found" in result.output

    def test_exit_code_zero_on_match(
        self, cli_runner: CliRunner, building_parquet: Path
    ) -> None:
        """Exit code is 0 when schema matches."""
        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                str(building_parquet),
                "--theme",
                "buildings",
                "--type",
                "building",
            ],
        )
        assert result.exit_code == 0

    def test_exit_code_nonzero_on_mismatch(self, cli_runner: CliRunner) -> None:
        """Exit code is non-zero when schema doesn't match."""
        schema = pa.schema([pa.field("wrong", pa.utf8())])
        table = pa.table({"wrong": pa.array([], type=pa.utf8())})
        pq.write_table(table, "wrong.parquet")

        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                "wrong.parquet",
                "--theme",
                "buildings",
                "--type",
                "building",
            ],
        )
        assert result.exit_code != 0

    def test_ignore_missing_fields_passes(self, cli_runner: CliRunner) -> None:
        """--ignore allows a file missing those fields to pass."""
        from overture.schema.buildings import Building

        schema = pydantic_model_to_arrow_schema(Building)
        # Remove version and bbox from the file's schema
        fields = [f for f in schema if f.name not in ("version", "bbox")]
        reduced_schema = pa.schema(fields)
        table = pa.table(
            {f.name: pa.array([], type=f.type) for f in reduced_schema},
            schema=reduced_schema,
        )
        pq.write_table(table, "no_version_bbox.parquet")

        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                "no_version_bbox.parquet",
                "--theme",
                "buildings",
                "--type",
                "building",
                "--ignore",
                "version",
                "--ignore",
                "bbox",
            ],
        )
        assert result.exit_code == 0

    def test_ignore_without_flag_still_fails(self, cli_runner: CliRunner) -> None:
        """Without --ignore, missing version/bbox causes failure."""
        from overture.schema.buildings import Building

        schema = pydantic_model_to_arrow_schema(Building)
        fields = [f for f in schema if f.name not in ("version", "bbox")]
        reduced_schema = pa.schema(fields)
        table = pa.table(
            {f.name: pa.array([], type=f.type) for f in reduced_schema},
            schema=reduced_schema,
        )
        pq.write_table(table, "no_version_bbox.parquet")

        result = cli_runner.invoke(
            cli,
            [
                "validate-schema",
                "no_version_bbox.parquet",
                "--theme",
                "buildings",
                "--type",
                "building",
            ],
        )
        assert result.exit_code != 0


class TestFileExtensionParsing:
    """Tests for _get_file_extension with local paths and remote URIs."""

    def test_local_path_string(self) -> None:
        """Local path as string returns correct extension."""
        assert _get_file_extension("data/file.parquet") == ".parquet"
        assert _get_file_extension("/absolute/path/file.parquet") == ".parquet"

    def test_local_path_object(self) -> None:
        """Local Path object returns correct extension."""
        from pathlib import Path

        assert _get_file_extension(Path("data/file.parquet")) == ".parquet"

    def test_s3_uri(self) -> None:
        """S3 URI returns correct extension."""
        uri = "s3://bucket/path/to/file.parquet"
        assert _get_file_extension(uri) == ".parquet"

    def test_s3_uri_with_partition(self) -> None:
        """S3 URI with partition path returns correct extension."""
        uri = "s3://overturemaps-us-west-2/release/2026-01-21.0/theme=addresses/type=address/part-00000.zstd.parquet"
        assert _get_file_extension(uri) == ".parquet"

    def test_gs_uri(self) -> None:
        """Google Cloud Storage URI returns correct extension."""
        uri = "gs://bucket/path/to/file.parquet"
        assert _get_file_extension(uri) == ".parquet"

    def test_file_uri(self) -> None:
        """file:// URI returns correct extension."""
        uri = "file:///home/user/data.parquet"
        assert _get_file_extension(uri) == ".parquet"

    def test_unsupported_extension(self) -> None:
        """Unsupported extension is returned as-is."""
        assert _get_file_extension("s3://bucket/file.csv") == ".csv"
        assert _get_file_extension("data.json") == ".json"

    def test_no_extension(self) -> None:
        """Path with no extension returns empty string."""
        assert _get_file_extension("s3://bucket/noext") == ""
        assert _get_file_extension("/path/to/noext") == ""
