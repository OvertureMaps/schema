"""
Dynamic Pydantic model creation with preservation of Overture metadata.
"""

from collections.abc import Callable
from typing import Any, TypeVar

import pydantic

from .metadata import Metadata

ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)


def create_model(
    model_name: str,
    /,
    *,
    __config__: pydantic.ConfigDict | None = None,
    __doc__: str | None = None,
    __base__: type[ModelT] | tuple[type[ModelT], ...] | None = None,
    __module__: str | None = None,
    __validators__: dict[str, Callable[..., Any]] | None = None,
    __cls_kwargs__: dict[str, Any] | None = None,
    __qualname__: str | None = None,
    __metadata__: Metadata | None = None,
    **field_definitions: Any | tuple[str, Any],
) -> type[ModelT]:
    """
    Dynamically create and return a new Pydantic model, preserving Overture metadata.

    Use `create_model` to dynamically create a subclass of any `BaseModel` while preserving Overture
    `Metadata`.

    ⚠️ Use this function instead of `pydantic.create_model`, as the Pydantic version will not
    preserve the metadata, which may result in your models not behaving as expected with Overture
    schema tooling. ⚠️

    If `__metadata__` is omitted or `None`, the metadata on the base model, if any, is propagated to
    the new model. If a non-`None` value is provided for `__metadata__`, the new model receives the
    new metadata and the metadata on the base model is not propagated.
    """
    model_class = pydantic.create_model(  # type: ignore[misc]
        model_name,
        __config__=__config__,
        __doc__=__doc__,
        __base__=__base__,  # type: ignore[arg-type]
        __module__=__module__,  # type: ignore[arg-type]
        __validators__=__validators__,
        __cls_kwargs__=__cls_kwargs__,
        __qualname__=__qualname__,
        **field_definitions,
    )
    if __metadata__ is not None:
        __metadata__.attach_to(model_class)
    elif __base__ is not None:
        prev = Metadata.retrieve_from(__base__, None)
        if prev is not None:
            prev.attach_to(model_class)
    return model_class  # type: ignore[return-value]
