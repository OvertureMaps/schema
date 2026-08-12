"""Add optional extension fields to existing discovered Pydantic models.

Model extensions declare their targets with `@extends`:

>>> class Place(BaseModel):
...     name: str
...
>>> @extends(Place)
... class OperatingHours(BaseModel):
...     primary: list[str]

Other types use `Extends` in `Annotated` metadata, optionally through
`NewType`:

>>> Capacity = NewType("Capacity", Annotated[int, Extends(Place)])

Targets may be models or model-bearing unions, `Annotated`, `NewType`, and
`RootModel` expressions. A `RootModel` is treated as an alias for its root
in both directions:

>>> class RoadSegment(BaseModel): ...
>>> class RailSegment(BaseModel): ...
>>> class Segment(RootModel):
...     root: RoadSegment | RailSegment

Targeting `Segment` with `@extends(Segment)` extends `RoadSegment` and
`RailSegment`, not `Segment` itself. Conversely, when `Segment` is a
registered entry, `create_extended_model` rebuilds it as a subclass whose
root annotation has the extended arms. The alias view also means a
`RootModel` over a non-model root is not a valid target:

>>> class Version(RootModel):
...     root: int
>>> Extends(Version)  # doctest: +ELLIPSIS
Traceback (most recent call last):
    ...
TypeError: `Extends` targets must be (or resolve to) pydantic `BaseModel` ...

`create_extended_model` likewise leaves `Version` untouched: its scalar
root contains nothing to extend. Types nested inside containers are not
traversed.

During discovery, each extension is exposed as a standalone one-field wrapper.
`create_extended_model` adds that field to every matching target model.
"""

import keyword
import logging
import types
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Annotated, Any, NewType, TypeVar, Union, get_args, get_origin

from pydantic import AliasChoices, AliasPath, BaseModel, RootModel

from overture.schema.system.create_model import create_model

log = logging.getLogger(__name__)

__all__ = [
    "Extends",
    "SelfReferentialRootError",
    "applied_extension_names",
    "applied_extensions",
    "create_extended_model",
    "extends",
    "extension_targets",
    "wrap_extension",
]


class SelfReferentialRootError(TypeError):
    """Raised when a `RootModel`'s root annotation reaches the model itself.

    Such a root has no finite shape, so it can be neither validated as an
    extension target nor rewritten by extension application. A dedicated
    class lets callers that must tolerate exactly this case (e.g. warning
    aggregation) catch it without swallowing unrelated `TypeError`s.
    """


# Class attributes this mechanism sets: qualified non-identifier names (the
# `Metadata` facility's convention), reachable only via getattr/setattr.

# On a wrapper model: the original (unwrapped) extension type expression.
_EXTENSION_ATTR = "_[overture.schema.system.extension]__extension"
# On an extended model: the names of the extensions it already carries.
_APPLIED_ATTR = "_[overture.schema.system.extension]__applied_extensions"
# On a model extension: the `Extends` metadata declared via `@extends`.
_EXTENDS_ATTR = "_[overture.schema.system.extension]__extends"


def applied_extensions(model_class: type[BaseModel]) -> frozenset[str]:
    """Return the names of the extensions `create_extended_model` has merged into `model_class`.

    Empty for a model with no extensions applied. Callers that need to know *whether* a
    particular field on a model came from an extension (e.g. to annotate generated docs) should
    check for that field's name in the returned set.
    """
    return getattr(model_class, _APPLIED_ATTR, frozenset())


def applied_extension_names(obj: Any) -> frozenset[str]:  # noqa: ANN401
    """Return the names of the extensions applied anywhere in a model-bearing type expression.

    Aggregates `applied_extensions` over every `BaseModel` leaf of `obj`, so it also covers
    union/`Annotated`/`NewType`/`RootModel` registry entries whose arms were extended
    individually. A self-referential `RootModel` yields the empty set instead of raising:
    such an entry cannot have been extended (`create_extended_model` refuses it), and this
    function feeds warning aggregation, which must not abort the extension pass.
    """
    try:
        classes = _unwrap_model_classes(obj)
    except SelfReferentialRootError:
        return frozenset()
    names: frozenset[str] = frozenset()
    for cls in classes:
        names |= applied_extensions(cls)
    return names


def _dedupe_targets(targets: Iterable[Any]) -> tuple[Any, ...]:
    """Deduplicate targets by equality, preserving order (targets may be unhashable)."""
    merged: list[Any] = []
    for target in targets:
        if target not in merged:
            merged.append(target)
    return tuple(merged)


def _self_referential_root_error(tp: type) -> SelfReferentialRootError:
    return SelfReferentialRootError(
        f"self-referential `RootModel` `{tp.__name__}` has no finite root shape"
    )


def _unwrap_model_classes(
    tp: Any,  # noqa: ANN401
    _seen: frozenset[type] = frozenset(),
) -> tuple[type[BaseModel], ...]:
    """Collect the concrete `BaseModel` classes a type expression resolves to.

    Unwraps `Annotated`, `Union` (including `X | Y`), `NewType`, and `RootModel` (an alias over
    its root value, so its root's classes are collected instead of the RootModel itself).
    Non-model leaves are ignored.
    """
    origin = get_origin(tp)
    if origin is Annotated:
        return _unwrap_model_classes(get_args(tp)[0], _seen)
    if origin is Union or origin is types.UnionType:
        classes: list[type[BaseModel]] = []
        for arg in get_args(tp):
            classes.extend(_unwrap_model_classes(arg, _seen))
        return tuple(classes)
    if hasattr(tp, "__supertype__"):
        return _unwrap_model_classes(tp.__supertype__, _seen)
    if isinstance(tp, type) and issubclass(tp, RootModel):
        if tp in _seen:
            raise _self_referential_root_error(tp)
        return _unwrap_model_classes(tp.model_fields["root"].annotation, _seen | {tp})
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return (tp,)
    return ()


def _is_model_target(
    tp: Any,  # noqa: ANN401
    _seen: frozenset[type] = frozenset(),
) -> bool:
    """Whether a type expression resolves *entirely* to extendable `BaseModel` subclasses.

    Unlike `_unwrap_model_classes`, a union must have *every* arm resolve to a model for the whole
    expression to qualify — a partially-model union (e.g. `Place | int`) is not a valid target.
    A `RootModel` qualifies exactly when its root does: it is an alias over its root value, so
    `RootModel[Road | Rail]` targets the arms while `RootModel[int]` resolves to no model.
    """
    origin = get_origin(tp)
    if origin is Annotated:
        return _is_model_target(get_args(tp)[0], _seen)
    if origin is Union or origin is types.UnionType:
        args = get_args(tp)
        return bool(args) and all(_is_model_target(arg, _seen) for arg in args)
    if hasattr(tp, "__supertype__"):
        return _is_model_target(tp.__supertype__, _seen)
    if isinstance(tp, type) and issubclass(tp, RootModel):
        if tp in _seen:
            raise _self_referential_root_error(tp)
        return _is_model_target(tp.model_fields["root"].annotation, _seen | {tp})
    return isinstance(tp, type) and issubclass(tp, BaseModel)


def _validate_targets(name: str, targets: tuple[Any, ...]) -> None:
    if not targets:
        raise TypeError(f"`{name}` requires at least one target model")
    for target in targets:
        if not _is_model_target(target):
            raise TypeError(
                f"`{name}` targets must be (or resolve to) pydantic `BaseModel` subclasses, "
                f"but {target!r} does not qualify. A `RootModel` target is an alias over its "
                f"root value, so its root must itself resolve to `BaseModel` subclasses."
            )


class Extends:
    """
    Metadata class for declaring, via `typing.Annotated`, which models a non-model extension targets.

    Use this for extensions that are not themselves Pydantic models (e.g. a scalar `NewType`). For
    model extensions, prefer the `@extends` decorator.
    """

    def __init__(self, *targets: Any) -> None:  # noqa: ANN401
        _validate_targets(type(self).__name__, targets)
        self.__targets = targets

    @property
    def extends(self) -> tuple[Any, ...]:
        return self.__targets


ModelT = TypeVar("ModelT", bound=BaseModel)


def extends(*targets: Any) -> Callable[[type[ModelT]], type[ModelT]]:  # noqa: ANN401
    """
    Decorate a Pydantic model to declare it is an extension of one or more target models.

    Parameters
    ----------
    targets
        One or more target model classes (or expressions resolving to `BaseModel` subclasses).

    Returns
    -------
    Callable
        A decorator that stashes the targets on the model as `Extends` metadata,
        introspectable via `extension_targets`; the decorated class is returned unchanged.
        Stacked decorators merge their target sets; a subclass's own declaration shadows
        an inherited one.
    """
    metadata = Extends(*targets)  # also validates the targets

    def decorator(model_class: type[ModelT]) -> type[ModelT]:
        if not (isinstance(model_class, type) and issubclass(model_class, BaseModel)):
            raise TypeError(
                f"`@{extends.__name__}` can only be applied to pydantic `BaseModel` subclasses, "
                f"but {model_class!r} is not one"
            )
        combined = metadata
        existing = model_class.__dict__.get(_EXTENDS_ATTR)
        if isinstance(existing, Extends):
            # Decorators apply bottom-up: `existing` came from the inner
            # (earlier) declaration, so its targets stay first.
            combined = Extends(*_dedupe_targets((*existing.extends, *metadata.extends)))
        setattr(model_class, _EXTENDS_ATTR, combined)
        return model_class

    return decorator


def _find_extends_metadata(tp: Any) -> tuple[Any, ...]:  # noqa: ANN401
    """Find `Extends` metadata attached to a `NewType`/`Annotated` expression.

    Multiple declarations in one `Annotated` frame merge; the nearest frame
    declaring any `Extends` decides.
    """
    if hasattr(tp, "__supertype__"):
        return _find_extends_metadata(tp.__supertype__)
    if get_origin(tp) is Annotated:
        args = get_args(tp)
        found = _dedupe_targets(
            target
            for meta in args[1:]
            if isinstance(meta, Extends)
            for target in meta.extends
        )
        if found:
            return found
        return _find_extends_metadata(args[0])
    return ()


def extension_targets(obj: Any) -> tuple[Any, ...]:  # noqa: ANN401
    """
    Return the target models an extension declares, or `()` if `obj` is not an extension.

    Detects all three declaration forms: a `BaseModel` carrying `Extends` metadata (via `@extends`),
    a `NewType` over `Annotated[..., Extends(...)]`, and a bare `Annotated[..., Extends(...)]`.
    """
    if isinstance(obj, type) and issubclass(obj, BaseModel):
        metadata = getattr(obj, _EXTENDS_ATTR, None)
        return metadata.extends if isinstance(metadata, Extends) else ()
    return _find_extends_metadata(obj)


def _wrapper_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_")) + "Extension"


def _validate_extension_name(name: str) -> None:
    """Reject entry-point names that cannot safely become a Pydantic field name.

    Covers non-identifiers/keywords, underscore- and ``model_``-prefixed names
    (private / protected in Pydantic), and `BaseModel` attribute names.
    """
    if (
        not name.isidentifier()
        or keyword.iskeyword(name)
        or name.startswith("_")
        or name.startswith("model_")
        or hasattr(BaseModel, name)
    ):
        raise ValueError(
            f"extension entry-point name {name!r} cannot be used as a field name: it must be "
            "a valid Python identifier, must not be a keyword or a `BaseModel` attribute name, "
            "and must not start with '_' or 'model_'"
        )


def wrap_extension(
    name: str,
    obj: Any,  # noqa: ANN401
    *,
    module: str | None = None,
) -> type[BaseModel] | None:
    """
    Wrap an extension entry-point value into a standalone wrapper model.

    The wrapper is a `BaseModel` with a single optional field named `name` holding the
    extension type. It carries `Extends` metadata and stashes the original (unwrapped)
    extension type (`_EXTENSION_ATTR`) so `create_extended_model` can reproduce the exact
    field annotation. Its `__module__` is the extension's defining module; a bare
    `Annotated[...]` has none of its own, so *module* (the entry point's module) fills the
    gap, falling back to this module.

    Returns `None` if `obj` is not an extension. Raises `ValueError` if `obj` is an extension
    but `name` cannot be used as a field name.
    """
    targets = extension_targets(obj)
    if not targets:
        return None
    _validate_extension_name(name)
    if get_origin(obj) is Annotated:
        # Annotated proxies attribute access to the wrapped type.
        owner_module = module or __name__
    else:
        owner_module = getattr(obj, "__module__", None) or module or __name__
    wrapper: type[BaseModel] = create_model(
        _wrapper_name(name),
        __module__=owner_module,
        __doc__=f"Standalone wrapper model for the `{name}` extension.",
        **{name: (obj | None, None)},  # type: ignore[arg-type]
    )
    setattr(wrapper, _EXTENDS_ATTR, Extends(*targets))
    setattr(wrapper, _EXTENSION_ATTR, obj)
    return wrapper


def _alias_strings(alias: object) -> Iterator[str]:
    """Yield the payload-level key names an alias declaration can claim."""
    if isinstance(alias, str):
        yield alias
    elif isinstance(alias, AliasPath):
        first = alias.path[0] if alias.path else None
        if isinstance(first, str):
            yield first
    elif isinstance(alias, AliasChoices):
        for choice in alias.choices:
            yield from _alias_strings(choice)


def _occupied_names(model: type[BaseModel]) -> set[str]:
    """Names an extension field may not use on `model`.

    Covers declared fields and their aliases, computed fields and their aliases, and every
    attribute defined anywhere on the class hierarchy (methods, properties, private
    attributes) — adding a field over any of these would break validation or shadow
    existing behavior.
    """
    names: set[str] = set(model.model_fields)
    for field_info in model.model_fields.values():
        for alias in (
            field_info.alias,
            field_info.validation_alias,
            field_info.serialization_alias,
        ):
            names.update(_alias_strings(alias))
    names.update(model.model_computed_fields)
    for computed_info in model.model_computed_fields.values():
        names.update(_alias_strings(computed_info.alias))
    for klass in model.__mro__:
        names.update(vars(klass))
    return names


def create_extended_model(
    model: Any,  # noqa: ANN401
    extensions: Mapping[str, type[BaseModel]],
    _seen: frozenset[type] = frozenset(),
) -> Any:  # noqa: ANN401
    """
    Apply extension wrappers to a model (or model-bearing type expression).

    Recurses through `Annotated`, `Union`, `NewType`, and `RootModel` (rewriting the root
    annotation in place) so discriminated-union entry points have every arm extended. For each
    concrete `BaseModel`, an optional field is added per extension whose targets the model is a
    subclass of. Returns the original expression unchanged when nothing applies, so identity is
    preserved for untouched types. Container types (`list[...]`, `dict[...]`) are opaque: models
    inside them are not rewritten.

    Parameters
    ----------
    model
        The model or type expression to extend.
    extensions
        Mapping of extension field name to wrapper model (as produced by `wrap_extension`).
        A raw `@extends` model class is also accepted and applies as its own field type.
    """
    origin = get_origin(model)

    if origin is Annotated:
        tp, *metadata = get_args(model)
        extended = create_extended_model(tp, extensions, _seen)
        if extended is tp:
            return model
        return Annotated.__class_getitem__((extended, *metadata))  # type: ignore[attr-defined]

    if origin is Union or origin is types.UnionType:
        args = get_args(model)
        extended_args = tuple(
            create_extended_model(arg, extensions, _seen) for arg in args
        )
        if all(new is old for new, old in zip(extended_args, args, strict=True)):
            return model
        # Rebuild via `Union[...]` rather than `reduce(or_, ...)`: `|` raises
        # on arms that don't implement it (e.g. an unresolved `ForwardRef`),
        # while `Union` accepts any type argument.
        return Union[extended_args]  # noqa: UP007

    if hasattr(model, "__supertype__"):
        supertype = model.__supertype__
        extended = create_extended_model(supertype, extensions, _seen)
        if extended is supertype:
            return model
        extended_alias = NewType(model.__name__, extended)  # type: ignore[misc, valid-type]
        # `NewType` stamps `__module__` from the calling frame and resets
        # `__qualname__`/`__doc__`; restore the original alias's identity so
        # the rebuilt alias doesn't appear to originate here and keeps any
        # custom docstring (which codegen renders).
        extended_alias.__module__ = model.__module__
        extended_alias.__qualname__ = model.__qualname__
        extended_alias.__doc__ = model.__doc__
        return extended_alias

    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        return model
    if issubclass(model, RootModel):
        # A RootModel is an alias over its root value: rewrite the root annotation and
        # rebuild as a subclass, reusing the root FieldInfo so its metadata, default,
        # and requiredness carry over.
        if model in _seen:
            raise _self_referential_root_error(model)
        root_field = model.model_fields["root"]
        extended = create_extended_model(
            root_field.annotation, extensions, _seen | {model}
        )
        if extended is root_field.annotation:
            return model
        return create_model(
            model.__name__,
            __base__=model,
            __module__=model.__module__,
            __doc__=model.__doc__,
            root=(extended, root_field),
        )

    applied: frozenset[str] = getattr(model, _APPLIED_ATTR, frozenset())
    occupied: set[str] | None = None
    fields: dict[str, tuple[Any, None]] = {}
    for field_name, wrapper in extensions.items():
        if field_name in applied:
            continue
        if not any(
            issubclass(model, cls)
            for target in extension_targets(wrapper)
            for cls in _unwrap_model_classes(target)
        ):
            continue
        if occupied is None:
            occupied = _occupied_names(model)
        if field_name in occupied:
            log.warning(
                "Extension '%s' collides with an existing field, alias, or attribute on "
                "model '%s'; skipping.",
                field_name,
                model.__name__,
            )
            continue
        # A wrapper built by `wrap_extension` stashes the original extension type;
        # a raw `@extends` model is itself the extension type.
        extension_type = getattr(wrapper, _EXTENSION_ATTR, wrapper)
        fields[field_name] = (extension_type | None, None)

    if not fields:
        return model

    extended_model = create_model(
        model.__name__,
        __base__=model,
        __doc__=model.__doc__,
        __module__=model.__module__,
        **fields,  # type: ignore[arg-type]
    )
    setattr(extended_model, _APPLIED_ATTR, applied | frozenset(fields))
    return extended_model
