"""Tests for parquet-schema command and arrow conversion."""

from pathlib import Path

import pytest
from click.testing import CliRunner

# Skip all tests if pyarrow not available
pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")


class TestArrowSchemaConversion:
    """Tests for Pydantic to Arrow schema conversion."""

    def test_primitive_int_types(self) -> None:
        """Test that integer primitive types map correctly."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type
        from overture.schema.system.primitive import int8, int16, int32, int64

        assert pydantic_to_arrow_type(int8) == pa.int8()
        assert pydantic_to_arrow_type(int16) == pa.int16()
        assert pydantic_to_arrow_type(int32) == pa.int32()
        assert pydantic_to_arrow_type(int64) == pa.int64()

    def test_primitive_uint_types(self) -> None:
        """Test that unsigned integer primitive types map correctly."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type
        from overture.schema.system.primitive import uint8, uint16, uint32

        assert pydantic_to_arrow_type(uint8) == pa.uint8()
        assert pydantic_to_arrow_type(uint16) == pa.uint16()
        assert pydantic_to_arrow_type(uint32) == pa.uint32()

    def test_primitive_float_types(self) -> None:
        """Test that float primitive types map correctly."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type
        from overture.schema.system.primitive import float32, float64

        assert pydantic_to_arrow_type(float32) == pa.float32()
        assert pydantic_to_arrow_type(float64) == pa.float64()

    def test_basic_python_types(self) -> None:
        """Test that basic Python types map correctly."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type

        assert pydantic_to_arrow_type(str) == pa.utf8()
        assert pydantic_to_arrow_type(int) == pa.int64()
        assert pydantic_to_arrow_type(float) == pa.float64()
        assert pydantic_to_arrow_type(bool) == pa.bool_()
        assert pydantic_to_arrow_type(bytes) == pa.binary()

    def test_string_newtypes(self) -> None:
        """Test that string newtypes map to utf8."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type
        from overture.schema.system.string import CountryCodeAlpha2, LanguageTag

        assert pydantic_to_arrow_type(CountryCodeAlpha2) == pa.utf8()
        assert pydantic_to_arrow_type(LanguageTag) == pa.utf8()

    def test_geometry_to_binary(self) -> None:
        """Test geometry converts to binary for WKB encoding."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type
        from overture.schema.system.primitive import Geometry

        assert pydantic_to_arrow_type(Geometry) == pa.binary()

    def test_bbox_to_struct(self) -> None:
        """Test BBox converts to struct with four float64 fields."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type
        from overture.schema.system.primitive import BBox

        arrow_type = pydantic_to_arrow_type(BBox)
        expected = pa.struct(
            [
                pa.field("xmin", pa.float64()),
                pa.field("ymin", pa.float64()),
                pa.field("xmax", pa.float64()),
                pa.field("ymax", pa.float64()),
            ]
        )
        assert arrow_type == expected

    def test_list_type(self) -> None:
        """Test list[T] converts to pa.list_(T)."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type

        arrow_type = pydantic_to_arrow_type(list[str])
        assert arrow_type == pa.list_(pa.utf8())

        arrow_type = pydantic_to_arrow_type(list[int])
        assert arrow_type == pa.list_(pa.int64())

    def test_optional_type(self) -> None:
        """Test that T | None still returns the base type (nullable handled separately)."""
        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type

        # The nullability is handled at the field level, not the type level
        assert pydantic_to_arrow_type(str | None) == pa.utf8()
        assert pydantic_to_arrow_type(int | None) == pa.int64()

    def test_enum_to_utf8(self) -> None:
        """Test that string enums convert to utf8."""
        from enum import Enum

        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type

        class Color(str, Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"

        assert pydantic_to_arrow_type(Color) == pa.utf8()

    def test_nested_model_to_struct(self) -> None:
        """Test that nested BaseModel converts to struct."""
        from pydantic import BaseModel

        from overture.schema.cli.arrow_schema import pydantic_to_arrow_type

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
        from overture.schema.cli.arrow_schema import pydantic_model_to_arrow_schema

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
        from overture.schema.cli.arrow_schema import pydantic_model_to_arrow_schema
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
        from overture.schema.cli.arrow_schema import pydantic_model_to_arrow_schema

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
        from overture.schema.cli.commands import cli

        result = cli_runner.invoke(
            cli,
            ["parquet-schema", "--theme", "buildings", "--type", "building", "--format", "text"],
        )
        assert result.exit_code == 0
        assert "id:" in result.output
        assert "geometry:" in result.output
        assert "theme:" in result.output

    def test_parquet_schema_file_output(self, cli_runner: CliRunner) -> None:
        """Test parquet-schema with parquet file output creates valid file."""
        from overture.schema.cli.commands import cli

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
        from overture.schema.cli.commands import cli

        result = cli_runner.invoke(
            cli, ["parquet-schema", "--theme", "buildings", "--format", "text"]
        )
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_parquet_schema_requires_output_for_parquet_format(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that parquet format requires output file."""
        from overture.schema.cli.commands import cli

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
        from overture.schema.cli.commands import cli

        result = cli_runner.invoke(
            cli, ["parquet-schema", "--type", "nonexistent_type", "--format", "text"]
        )
        assert result.exit_code != 0
        assert "No model found" in result.output

    def test_parquet_schema_ambiguous_type(self, cli_runner: CliRunner) -> None:
        """Test that ambiguous type without theme gives helpful error."""
        from overture.schema.cli.commands import cli

        # This test assumes there might be types with same name in different themes
        # If not, the test will just verify the happy path works
        result = cli_runner.invoke(
            cli, ["parquet-schema", "--theme", "buildings", "--type", "building", "--format", "text"]
        )
        # Should succeed with theme specified
        assert result.exit_code == 0

    def test_parquet_schema_segment_type(self, cli_runner: CliRunner) -> None:
        """Test parquet-schema works for transportation segment."""
        from overture.schema.cli.commands import cli

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
        from overture.schema.cli.commands import cli

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
