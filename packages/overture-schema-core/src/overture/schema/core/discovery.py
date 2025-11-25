"""Model discovery system for Overture schema registry."""

import importlib.metadata
import logging
from dataclasses import dataclass

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ModelKey:
    """Key identifying a registered model by namespace, theme, and type.

    Attributes
    ----------
    namespace : str
        The namespace (e.g., "overture", "annex")
    theme : str | None
        The theme name (e.g., "buildings", "places"), or None for non-themed models
    type : str
        The feature type (e.g., "building", "place")
    class_name : str
        The fully qualified class name from the entry point value

    """

    namespace: str
    theme: str | None
    type: str
    class_name: str


def discover_models(
    namespace: str | None = None,
) -> dict[ModelKey, type[BaseModel]]:
    """Discover all registered Overture models via entry points.

    Parameters
    ----------
    namespace : str | None, optional
        Optional namespace filter. If provided, only models from this
        namespace will be returned (e.g., "overture", "annex").

    Returns
    -------
    dict[ModelKey, type[BaseModel]]
        Dict mapping ModelKey to model classes.
        Theme will be None for entries without an explicit theme component.

    Notes
    -----
    Entry point name format:
        - Core themes: "overture:<theme>:<type>"
        - Non-core (2-part): "annex:<type>" (theme will be None)
        - Non-core (3-part): "annex:<theme>:<type>"

    """
    models = {}
    try:
        for entry_point in importlib.metadata.entry_points(group="overture.models"):
            # Parse namespace:theme:type or namespace:type from entry point name
            parts = entry_point.name.split(":", 2)

            if len(parts) == 2:
                # namespace:type format (no theme)
                ns, feature_type = parts
                theme = None
            elif len(parts) == 3:
                # namespace:theme:type format
                ns, theme, feature_type = parts
            else:
                logger.warning(
                    "Invalid entry point format %s, expected namespace:theme:type or namespace:type",
                    entry_point.name,
                )
                continue

            # Filter by namespace if specified
            if namespace is not None and ns != namespace:
                continue

            try:
                model_class = entry_point.load()
                key = ModelKey(
                    namespace=ns,
                    theme=theme,
                    type=feature_type,
                    class_name=entry_point.value,
                )
                models[key] = model_class
            except Exception as e:
                # Log warning but don't fail for individual models
                logger.warning("Could not load model %s: %s", entry_point.name, e)
    except Exception as e:
        logger.warning("Could not discover entry points: %s", e)

    return models


def get_registered_model(
    namespace: str, feature_type: str, theme: str | None = None
) -> type[BaseModel] | None:
    """Get the Pydantic model for a namespace/theme/type combination.

    This uses setuptools entry points for registration.

    Parameters
    ----------
    namespace : str
        The namespace (e.g., "overture", "annex")
    feature_type : str
        The type name
    theme : str | None, optional
        The theme name (optional)

    Returns
    -------
    type[BaseModel] | None
        The model class if found, None otherwise.

    """
    # Check all discovered models for a match
    models = discover_models(namespace=namespace)
    # Need to find by namespace/theme/type, not exact key match
    for key, model_class in models.items():
        if (
            key.namespace == namespace
            and key.theme == theme
            and key.type == feature_type
        ):
            return model_class
    return None
