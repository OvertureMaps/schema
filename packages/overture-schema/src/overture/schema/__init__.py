__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from functools import reduce
from operator import or_
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, Field

from overture.schema.core import parse_feature
from overture.schema.core.discovery import discover_models
from overture.schema.core.json_schema import json_schema


def parse(feature: dict[str, Any], mode: str = "json") -> dict[str, Any] | None:
    """Parse and validate a feature using the union of all available models.

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
        model_union = Any
    else:
        # Filter out BaseModel types without a 'type' field; they can't be discriminated
        # This is an Overture-specific optimization, as our core models all have 'type'
        discriminated_models = []
        non_discriminated_models = []

        for model in models.values():
            if (
                isinstance(model, type)
                and issubclass(model, BaseModel)
                and "type" not in model.model_fields
            ):
                non_discriminated_models.append(model)
            else:
                # Include union types and models with 'type' field
                discriminated_models.append(model)

        assert discriminated_models or non_discriminated_models

        discriminated_union = None
        if discriminated_models:
            discriminated_union = Annotated[
                reduce(or_, discriminated_models), Field(discriminator="type")
            ]

        non_discriminated_union = reduce(or_, non_discriminated_models, None)

        if discriminated_union and non_discriminated_union:
            model_union = discriminated_union | non_discriminated_union
        elif discriminated_union:
            model_union = discriminated_union
        else:
            model_union = non_discriminated_union

    return parse_feature(feature, model_union, mode)


__all__ = [
    "parse",
    "parse_feature",
    "json_schema",
]
