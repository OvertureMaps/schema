from typing import Any, get_origin

from pydantic import BaseModel

from ._cache import get_type_adapter


def json_schema(models: type[BaseModel] | Any) -> dict[str, Any]:
    """Generate JSON schema for a Pydantic model or union of models.

    Args:
        models: Either a Pydantic BaseModel class or a union type (possibly
                annotated with discriminator information) of BaseModels.

    Returns:
        dict: JSON schema representation of the model(s).

    Raises:
        TypeError: If models is not a BaseModel or union type.
    """
    if isinstance(models, type) and issubclass(models, BaseModel):
        return models.model_json_schema()

    if get_origin(models) is not None:
        adapter = get_type_adapter(models)
        return adapter.json_schema()

    raise TypeError(f"Expected BaseModel or union type, got {type(models)}")
