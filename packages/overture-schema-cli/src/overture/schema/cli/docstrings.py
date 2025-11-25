"""Docstring utilities for extracting documentation from modules and models."""

import inspect

from pydantic import BaseModel


def get_theme_module_docstring(theme_name: str) -> str | None:
    """Get the docstring of a theme module if available."""
    try:
        # Try to import the theme module
        module_name = f"overture.schema.{theme_name}"
        module = __import__(module_name, fromlist=[""])
        return inspect.getdoc(module)
    except (ImportError, AttributeError):
        return None


def get_model_docstring(model_class: type[BaseModel]) -> str | None:
    """Get a clean, formatted docstring from a model class."""
    return inspect.getdoc(model_class)
