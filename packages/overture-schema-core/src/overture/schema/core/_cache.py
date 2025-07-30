from typing import Any

from pydantic import TypeAdapter

# Shared cache for TypeAdapter instances to avoid recreating them
_TYPE_ADAPTER_CACHE: dict[Any, TypeAdapter] = {}


def get_type_adapter(model_type: Any) -> TypeAdapter:
    """Get a cached TypeAdapter instance for the given model type.

    Args:
        model_type: The type to create/retrieve a TypeAdapter for

    Returns:
        TypeAdapter instance for the given type
    """
    if model_type not in _TYPE_ADAPTER_CACHE:
        _TYPE_ADAPTER_CACHE[model_type] = TypeAdapter(model_type)
    return _TYPE_ADAPTER_CACHE[model_type]
