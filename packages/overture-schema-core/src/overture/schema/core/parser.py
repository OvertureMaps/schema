from types import UnionType
from typing import Any, cast

from pydantic import BaseModel

from ._cache import get_type_adapter


def parse_feature(
    feature: dict[str, Any],
    model_type: type[BaseModel] | UnionType | type,
    mode: str = "json",
) -> dict[str, Any] | None:
    """Parse and validate a feature using the provided model type.

    Args:
        feature: Feature data (GeoJSON or flattened format)
        model_type: Pydantic model type or union type to validate against
        mode: Output mode - "json" for GeoJSON format, "python" for flattened format

    Returns:
        Parsed feature in the specified format

    Supports both GeoJSON format (with nested properties) and flattened format.
    """

    try:
        # Basic structure validation
        if not isinstance(feature, dict):
            raise ValueError("Feature must be an object")

        # Detect format and normalize to flattened structure
        if "properties" in feature and feature.get("type") == "Feature":
            # GeoJSON format - flatten it
            flattened_feature = {
                "id": feature["id"],
                "geometry": feature["geometry"],
                **feature["properties"],  # Flatten properties into top level
            }
        else:
            # Already flattened format
            flattened_feature = feature.copy()

        adapter = get_type_adapter(model_type)
        parsed_model = adapter.validate_python(flattened_feature)

        # Return using the requested mode
        return cast(
            dict[str, Any],
            parsed_model.model_dump(exclude_unset=True, mode=mode, by_alias=True),
        )
    except Exception as e:
        raise ValueError(str(e)) from e
