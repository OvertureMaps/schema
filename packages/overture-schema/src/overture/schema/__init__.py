__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from functools import reduce
from operator import or_
from types import UnionType
from typing import TYPE_CHECKING, Annotated, Any, Union

from pydantic import Field

from overture.schema.addresses import Address
from overture.schema.core import parse_feature
from overture.schema.core.discovery import discover_models

Types = Annotated[
    Address,
    Field(discriminator="type"),
]


def parse(feature: dict[str, Any], mode: str = "json") -> dict[str, Any] | None:
    """
    Parse and validate a feature using the union of all available models.

    Args:
        feature: Feature data (GeoJSON or flattened format)
        mode: Output mode - "json" for GeoJSON format, "python" for flattened format

    Returns:
        Parsed feature in the specified format

    Uses the discovery mechanism to find all registered models and validates
    the feature against the union of all available models.
    """
    # Discover all registered models via entry points
    models = discover_models()
    if not models:
        raise ValueError("No registered models found via entry points")

    if TYPE_CHECKING:
        # For type checking, use Any to avoid mypy errors with dynamic types
        DiscriminatedUnion = Annotated[Any, Field(discriminator="type")]
    else:
        # Create a discriminated union for use at runtime
        union_type = reduce(or_, list(models.values()))
        DiscriminatedUnion = Annotated[union_type, Field(discriminator="type")]

    return parse_feature(feature, DiscriminatedUnion, mode)
