"""
Dynamic Pydantic model creation with preservation of Overture metadata.
"""

import warnings
from collections.abc import Callable
from typing import Any, TypeVar, cast

import pydantic
from typing_extensions import TypeForm, deprecated

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
    **field_definitions: TypeForm[object] | tuple[TypeForm[object], Any],
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

    If the base model declares a PEP 702 `@deprecated` itself, the new model declares it too, with
    the same message and warning category. The new model stands in for its base -- the
    model-constraint decorators and `@scoped` return it in place of the class they decorate -- so
    decorator order must not decide whether the exported class is deprecated. Deriving it does not
    raise the warning PEP 702 issues on subclassing a deprecated class, and subclassing it raises
    that warning once, however many models were derived between it and the deprecated base.
    """
    model_class = _derive_keeping_deprecation(
        __base__,
        lambda: pydantic.create_model(  # type: ignore[misc]
            model_name,
            __config__=__config__,
            __doc__=__doc__,
            __base__=__base__,  # type: ignore[arg-type]
            __module__=__module__,  # type: ignore[arg-type]
            __validators__=__validators__,
            __cls_kwargs__=__cls_kwargs__,
            __qualname__=__qualname__,
            # mypy checks an unpacked dict against every keyword parameter, `__base__` included,
            # so the field definitions go through as `Any`.
            **cast(dict[str, Any], field_definitions),
        ),
    )
    if __metadata__ is not None:
        __metadata__.attach_to(model_class)
    elif __base__ is not None:
        prev = Metadata.retrieve_from(__base__, None)
        if prev is not None:
            prev.attach_to(model_class)
    return model_class  # type: ignore[return-value]


def _derive_keeping_deprecation(
    base: object, derive: Callable[[], type[pydantic.BaseModel]]
) -> type[pydantic.BaseModel]:
    """
    Run `derive` and give the class it returns the deprecation `base` declares, if any.

    The warning PEP 702 raises on subclassing `base` is suppressed. The warning category lives only
    in the closures `@deprecated` installs, so it is recovered from that suppressed warning; a base
    deprecated with `category=None` raises none, and the derived class is deprecated the same way.
    Any other warning `derive` raises is re-issued.
    """
    message = base.__dict__.get("__deprecated__") if isinstance(base, type) else None
    if not isinstance(message, str):
        return derive()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        derived = derive()
    subclass_warnings = [w for w in caught if str(w.message) == message]
    for w in caught:
        if w not in subclass_warnings:
            warnings.warn_explicit(w.message, w.category, w.filename, w.lineno)
    category = subclass_warnings[0].category if subclass_warnings else None
    declares_init_subclass = "__init_subclass__" in derived.__dict__
    derived = deprecated(message, category=category)(derived)
    if category is not None and not declares_init_subclass:
        # The wrapper PEP 702 installs warns, then calls the next `__init_subclass__` in the MRO,
        # which is the base's wrapper, already warning with the same message and category.
        # Removing it leaves subclassing to that one warning instead of one per derived layer.
        del derived.__init_subclass__
    return derived
