import importlib.metadata
from typing import cast

from pydantic import BaseModel


def discover_models() -> dict[tuple[str, str], type[BaseModel]]:
    """Discover all registered Overture models via entry points."""

    models = {}
    try:
        for entry_point in importlib.metadata.entry_points(group="overture.models"):
            # Parse theme.type from entry point name
            # TODO add a 3rd component: namespace
            theme, feature_type = entry_point.name.split(".", 1)
            try:
                model_class = entry_point.load()
                models[(theme, feature_type)] = model_class
            except Exception as e:
                # Log warning but don't fail for individual models
                print(f"Warning: Could not load model {entry_point.name}: {e}")
    except Exception as e:
        print(f"Warning: Could not discover entry points: {e}")

    return models


def get_registered_model(theme: str, feature_type: str) -> type[BaseModel] | None:
    """Get the Pydantic model for a theme/type combination. This uses setuptools entry points for registration."""

    entry_point_name = f"{theme}.{feature_type}"
    try:
        for entry_point in importlib.metadata.entry_points(group="overture.models"):
            if entry_point.name == entry_point_name:
                return cast(type[BaseModel], entry_point.load())
    except Exception as e:
        print(f"Warning: Could not load model {entry_point_name}: {e}")

    return None
