from types import UnionType

from pydantic import BaseModel, TypeAdapter

# Shared cache for TypeAdapter instances to avoid recreating them
_TYPE_ADAPTER_CACHE: dict[type[BaseModel] | UnionType | type, TypeAdapter] = {}


def get_type_adapter(model_type: type[BaseModel] | UnionType | type) -> TypeAdapter:
    """Get a cached TypeAdapter instance for the given model type.

    Args:
        model_type: The type to create/retrieve a TypeAdapter for

    Returns:
        TypeAdapter instance for the given type
    """
    if model_type not in _TYPE_ADAPTER_CACHE:
        _TYPE_ADAPTER_CACHE[model_type] = TypeAdapter(model_type)
    return _TYPE_ADAPTER_CACHE[model_type]
