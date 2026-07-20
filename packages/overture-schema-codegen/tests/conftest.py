"""Shared pytest fixtures for overture-schema-codegen tests."""

import overture.schema.system.geometric as _system_geometric
import overture.schema.system.numeric as _system_numeric
import pytest
from click.testing import CliRunner
from codegen_test_support import find_model_class
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.numeric_extraction import extract_numerics
from overture.schema.codegen.extraction.specs import RecordSpec
from overture.schema.codegen.markdown.pipeline import (
    partition_numeric_and_geometry_types,
)
from overture.schema.codegen.markdown.renderer import (
    render_geometry_from_values,
    render_numeric_from_specs,
)
from overture.schema.system.discovery import discover_models
from overture.schema.system.geometric import GeometryType
from pydantic import BaseModel


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Regenerate golden files instead of comparing against them",
    )


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--update-golden"))


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def all_discovered_models() -> dict:
    """Discover and return all registered Overture models."""
    return discover_models()


@pytest.fixture
def building_class(all_discovered_models: dict) -> type[BaseModel]:
    """Get the Building model class."""
    return find_model_class("Building", all_discovered_models)


@pytest.fixture
def building_spec(building_class: type[BaseModel]) -> RecordSpec:
    """Extract the Building model spec."""
    return extract_model(building_class)


@pytest.fixture
def place_class(all_discovered_models: dict) -> type[BaseModel]:
    """Get the Place model class."""
    return find_model_class("Place", all_discovered_models)


@pytest.fixture
def division_class(all_discovered_models: dict) -> type[BaseModel]:
    """Get the Division model class."""
    return find_model_class("Division", all_discovered_models)


@pytest.fixture(scope="module")
def numeric_markdown() -> str:
    """Render the numeric.md page from the system numeric module."""
    numeric_names, _ = partition_numeric_and_geometry_types(
        _system_numeric, _system_geometric
    )
    return render_numeric_from_specs(extract_numerics(numeric_names))


@pytest.fixture(scope="module")
def geometry_markdown() -> str:
    """Render the geometric.md page from system GeometryType values."""
    return render_geometry_from_values([m.value for m in GeometryType])
