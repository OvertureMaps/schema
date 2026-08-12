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
from typing import (
    Annotated,
    Any,
    NewType,
    TypeAlias,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import AliasChoices, AliasPath, BaseModel, RootModel
from typing_extensions import TypeForm

from overture.schema.system.create_model import create_model
from overture.schema.system.typing_util import (
    is_newtype,
    model_types,
    non_model_parts,
)

log = logging.getLogger(__name__)

__all__ = [
    "Extends",
    "ExtensionTarget",
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


# What an extension may declare it extends: a type expression -- model class,
# model union, `Annotated`, `NewType`, `RootModel` -- whose meaning resolves to
# `BaseModel`. Static checkers verify this shape at the declaration site;
# `_validate_targets` remains the runtime gate for what they cannot see
# (scalar `RootModel` roots, self-referential roots).
ExtensionTarget: TypeAlias = TypeForm[BaseModel]


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


def applied_extension_names(obj: object) -> frozenset[str]:
    """Return the names of the extensions applied anywhere in a model-bearing type expression.

    Aggregates `applied_extensions` over every model type of `obj`, so it also covers
    union/`Annotated`/`NewType`/`RootModel` registry entries whose arms were extended
    individually. A self-referential `RootModel` yields the empty set instead of raising:
    such an entry cannot have been extended (`create_extended_model` refuses it), and this
    function feeds warning aggregation, which must not abort the extension pass.
    """
    try:
        classes = _target_model_types(obj)
    except SelfReferentialRootError:
        return frozenset()
    names: frozenset[str] = frozenset()
    for cls in classes:
        names |= applied_extensions(cls)
    return names


_ItemT = TypeVar("_ItemT")


def _dedupe_targets(targets: Iterable[_ItemT]) -> tuple[_ItemT, ...]:
    """Deduplicate targets by equality, preserving order (targets may be unhashable)."""
    merged: list[_ItemT] = []
    for target in targets:
        if target not in merged:
            merged.append(target)
    return tuple(merged)


def _self_referential_root_error(tp: type) -> SelfReferentialRootError:
    return SelfReferentialRootError(
        f"self-referential `RootModel` `{tp.__name__}` has no finite root shape"
    )


def _target_model_types(
    tp: object, _seen: frozenset[type] = frozenset()
) -> tuple[type[BaseModel], ...]:
    """Model types of a type expression, with `RootModel` treated as an alias over its root.

    Each `RootModel` is replaced by its root annotation's model types, recursively; a
    self-referential root raises `TypeError` (it has no finite shape).
    """
    classes: list[type[BaseModel]] = []
    for model_type in model_types(tp):
        if issubclass(model_type, RootModel):
            if model_type in _seen:
                raise _self_referential_root_error(model_type)
            classes.extend(
                _target_model_types(
                    model_type.model_fields["root"].annotation, _seen | {model_type}
                )
            )
        else:
            classes.append(model_type)
    return tuple(classes)


def _is_valid_target(tp: object, _seen: frozenset[type] = frozenset()) -> bool:
    """Whether a type expression resolves *entirely* to extendable `BaseModel` subclasses.

    A partially-model union (e.g. `Place | int`) does not qualify. A `RootModel` qualifies
    exactly when its root does: it is an alias over its root value, so `RootModel[Road | Rail]`
    targets the arms while `RootModel[int]` resolves to no model.
    """
    if non_model_parts(tp):
        return False
    resolved = model_types(tp)
    if not resolved:
        return False
    for model_type in resolved:
        if issubclass(model_type, RootModel):
            if model_type in _seen:
                raise _self_referential_root_error(model_type)
            if not _is_valid_target(
                model_type.model_fields["root"].annotation, _seen | {model_type}
            ):
                return False
    return True


def _validate_targets(name: str, targets: tuple[object, ...]) -> None:
    if not targets:
        raise TypeError(f"`{name}` requires at least one target model")
    for target in targets:
        if not _is_valid_target(target):
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

    def __init__(self, *targets: ExtensionTarget) -> None:
        _validate_targets(type(self).__name__, targets)
        self.__targets = targets

    @property
    def extends(self) -> tuple[ExtensionTarget, ...]:
        return self.__targets


ModelT = TypeVar("ModelT", bound=BaseModel)


def extends(*targets: ExtensionTarget) -> Callable[[type[ModelT]], type[ModelT]]:
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


def _find_extends_metadata(tp: object) -> tuple[ExtensionTarget, ...]:
    """Find `Extends` metadata attached to a `NewType`/`Annotated` expression.

    Multiple declarations in one `Annotated` frame merge; the nearest frame
    declaring any `Extends` decides.
    """
    if is_newtype(tp):
        return _find_extends_metadata(tp.__supertype__)  # type: ignore[attr-defined]
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


def extension_targets(obj: object) -> tuple[ExtensionTarget, ...]:
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
    obj: object,
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
        **{name: (cast(Any, obj) | None, None)},  # type: ignore[arg-type]
    )
    setattr(wrapper, _EXTENDS_ATTR, Extends(*targets))
    setattr(wrapper, _EXTENSION_ATTR, obj)
    return wrapper


def _alias_strings(alias: str | AliasPath | AliasChoices | None) -> Iterator[str]:
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
    model: object,
    extensions: Mapping[str, type[BaseModel]],
) -> object:
    """
    Apply extension wrappers to a model (or model-bearing type expression).

    Recurses through `Annotated`, `Union`, `NewType`, and `RootModel` (rewriting the root
    annotation in place) so discriminated-union entry points have every arm extended. For each
    concrete `BaseModel`, an optional field is added per extension whose targets the model is a
    subclass of. Returns the original expression unchanged when nothing applies, so identity is
    preserved for untouched types. Container types (`list[...]`, `dict[...]`) are opaque: models
    inside them are not rewritten.

    The signature is deliberately `object -> object`: the transformation rewrites arbitrary
    runtime type expressions, and no static type describes it meaningfully. A caller that knows
    it supplied a model class must narrow the result before using it as one.

    Parameters
    ----------
    model
        The model or type expression to extend.
    extensions
        Mapping of extension field name to wrapper model (as produced by `wrap_extension`).
        A raw `@extends` model class is also accepted and applies as its own field type.
    """
    return _extend_type_expression(model, extensions, frozenset())


def _extend_type_expression(
    expression: object,
    extensions: Mapping[str, type[BaseModel]],
    seen: frozenset[type],
) -> object:
    """Recursive worker for `create_extended_model`.

    `seen` carries the `RootModel` classes on the current descent so a
    self-referential root fails loudly instead of recursing forever; keeping
    it here leaves the public signature free of cycle-detection state.
    """
    origin = get_origin(expression)

    if origin is Annotated:
        tp, *metadata = get_args(expression)
        extended = _extend_type_expression(tp, extensions, seen)
        if extended is tp:
            return expression
        return Annotated.__class_getitem__(  # type: ignore[attr-defined]
            (extended, *metadata)
        )

    if origin is Union or origin is types.UnionType:
        args = get_args(expression)
        extended_args = tuple(
            _extend_type_expression(arg, extensions, seen) for arg in args
        )
        if all(new is old for new, old in zip(extended_args, args, strict=True)):
            return expression
        # Rebuild via `Union[...]` rather than `reduce(or_, ...)`: `|` raises
        # on arms that don't implement it (e.g. an unresolved `ForwardRef`),
        # while `Union` accepts any type argument.
        return Union[extended_args]  # noqa: UP007

    if is_newtype(expression):
        supertype = expression.__supertype__  # type: ignore[attr-defined]
        extended = _extend_type_expression(supertype, extensions, seen)
        if extended is supertype:
            return expression
        extended_alias = NewType(expression.__name__, extended)  # type: ignore[misc, valid-type, attr-defined]
        # `NewType` stamps `__module__` from the calling frame and resets
        # `__qualname__`/`__doc__`; restore the original alias's identity so
        # the rebuilt alias doesn't appear to originate here and keeps any
        # custom docstring (which codegen renders).
        extended_alias.__module__ = expression.__module__  # type: ignore[attr-defined]
        extended_alias.__qualname__ = expression.__qualname__  # type: ignore[attr-defined]
        extended_alias.__doc__ = expression.__doc__
        return extended_alias

    if not (isinstance(expression, type) and issubclass(expression, BaseModel)):
        return expression
    if issubclass(expression, RootModel):
        # A RootModel is an alias over its root value: rewrite the root annotation and
        # rebuild as a subclass, reusing the root FieldInfo so its metadata, default,
        # and requiredness carry over.
        if expression in seen:
            raise _self_referential_root_error(expression)
        root_field = expression.model_fields["root"]
        extended = _extend_type_expression(
            root_field.annotation, extensions, seen | {expression}
        )
        if extended is root_field.annotation:
            return expression
        return create_model(
            expression.__name__,
            __base__=expression,
            __module__=expression.__module__,
            __doc__=expression.__doc__,
            root=(extended, root_field),
        )

    applied = applied_extensions(expression)
    occupied: set[str] | None = None
    fields: dict[str, tuple[Any, None]] = {}
    for field_name, wrapper in extensions.items():
        if field_name in applied:
            continue
        if not any(
            issubclass(expression, target_model)
            for target in extension_targets(wrapper)
            for target_model in _target_model_types(target)
        ):
            continue
        if occupied is None:
            occupied = _occupied_names(expression)
        if field_name in occupied:
            log.warning(
                "Extension '%s' collides with an existing field, alias, or attribute on "
                "model '%s'; skipping.",
                field_name,
                expression.__name__,
            )
            continue
        # A wrapper built by `wrap_extension` stashes the original extension type;
        # a raw `@extends` model is itself the extension type.
        extension_type: object = getattr(wrapper, _EXTENSION_ATTR, wrapper)
        fields[field_name] = (cast(Any, extension_type) | None, None)

    if not fields:
        return expression

    extended_model = create_model(
        expression.__name__,
        __base__=expression,
        __doc__=expression.__doc__,
        __module__=expression.__module__,
        **fields,  # type: ignore[arg-type]
    )
    setattr(extended_model, _APPLIED_ATTR, applied | frozenset(fields))
    return extended_model
