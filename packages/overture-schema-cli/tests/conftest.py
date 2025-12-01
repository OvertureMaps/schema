"""Shared test fixtures for CLI tests."""

from collections.abc import Generator
from io import StringIO
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from rich.console import Console


@pytest.fixture
def cli_runner() -> Generator[CliRunner, None, None]:
    """Provide a CliRunner within an isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


@pytest.fixture
def stderr_buffer() -> Generator[StringIO, None, None]:
    """Provide a patched stderr buffer for capturing CLI error output."""
    buffer = StringIO()
    captured_console = Console(file=buffer, force_terminal=False)

    with patch("overture.schema.cli.commands.stderr", captured_console):
        yield buffer


@pytest.fixture
def building_feature_yaml_content() -> str:
    """Return YAML content for a valid building feature."""
    return """
id: test
type: Feature
geometry:
  type: Polygon
  coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
properties:
  theme: buildings
  type: building
  version: 0
"""


@pytest.fixture
def building_feature_yaml(
    cli_runner: CliRunner, building_feature_yaml_content: str
) -> str:
    """Create a test.yaml file with valid building feature in isolated filesystem."""
    filename = "test.yaml"
    with open(filename, "w") as f:
        f.write(building_feature_yaml_content)
    return filename


@pytest.fixture
def missing_id_yaml_content() -> str:
    """Return YAML content with missing required field."""
    return """
type: Feature
geometry:
  type: Polygon
  coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
properties:
  theme: buildings
  type: building
  version: 0
"""


def build_feature(
    id: str | None = "test",
    theme: str | None = "buildings",
    type: str = "building",
    geometry_type: str = "Polygon",
    coordinates: list | None = None,
    version: int | None = 0,
    geojson_format: bool = True,
    **properties: Any,
) -> dict[str, Any]:
    """Build a feature dictionary with the specified parameters.

    Args:
        id: Feature ID (None to omit)
        theme: Theme name (None to omit)
        type: Feature type
        geometry_type: Geometry type (Point, Polygon, etc.)
        coordinates: Custom coordinates (None for sensible defaults)
        version: Feature version (None to omit)
        geojson_format: If True, use GeoJSON format; if False, use flat format
        **properties: Additional properties to include

    Returns:
        Feature dictionary in the requested format
    """
    # Default coordinates based on geometry type
    if coordinates is None:
        if geometry_type == "Point":
            coordinates = [0.0, 0.0]
        elif geometry_type == "Polygon":
            coordinates = [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        elif geometry_type == "LineString":
            coordinates = [[0, 0], [1, 1]]
        elif geometry_type == "MultiPolygon":
            coordinates = [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]]
        else:
            coordinates = []

    geometry = {"type": geometry_type, "coordinates": coordinates}

    if geojson_format:
        # GeoJSON format: properties nested under "properties" key
        props: dict[str, Any] = {
            "type": type,
            **properties,
        }
        if theme is not None:
            props["theme"] = theme
        if version is not None:
            props["version"] = version

        feature: dict[str, Any] = {
            "type": "Feature",
            "geometry": geometry,
            "properties": props,
        }
        if id is not None:
            feature["id"] = id
    else:
        # Flat format: properties at top level
        # Build in the expected order: geometry, theme, type, version, id, properties
        feature = {"geometry": geometry}
        if theme is not None:
            feature["theme"] = theme
        feature["type"] = type
        if version is not None:
            feature["version"] = version
        feature.update(properties)
        if id is not None:
            feature["id"] = id

    return feature
