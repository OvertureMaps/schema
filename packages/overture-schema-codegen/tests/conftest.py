"""Shared pytest fixtures for overture-schema-codegen tests."""

import pytest
from overture.schema.codegen.model_extraction import extract_model
from overture.schema.codegen.specs import ModelSpec
from overture.schema.core.discovery import discover_models
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


def _find_model_class(name: str, models: dict[object, object]) -> type[BaseModel]:
    """Find a discovered model class by name."""
    matches = [v for v in models.values() if getattr(v, "__name__", None) == name]
    assert matches, f"{name} model not found"
    match = matches[0]
    assert isinstance(match, type)
    assert issubclass(match, BaseModel)
    return match


@pytest.fixture
def all_discovered_models() -> dict:
    """Discover and return all registered Overture models."""
    return discover_models()


@pytest.fixture
def building_class(all_discovered_models: dict) -> type[BaseModel]:
    """Get the Building model class."""
    return _find_model_class("Building", all_discovered_models)


@pytest.fixture
def building_spec(building_class: type[BaseModel]) -> ModelSpec:
    """Extract the Building model spec."""
    return extract_model(building_class)


@pytest.fixture
def place_class(all_discovered_models: dict) -> type[BaseModel]:
    """Get the Place model class."""
    return _find_model_class("Place", all_discovered_models)


@pytest.fixture
def division_class(all_discovered_models: dict) -> type[BaseModel]:
    """Get the Division model class."""
    return _find_model_class("Division", all_discovered_models)
