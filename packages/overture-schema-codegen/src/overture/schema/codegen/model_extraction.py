"""Model extraction and tree expansion."""

from __future__ import annotations

import dataclasses

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from overture.schema.system.model_constraint import ModelConstraint

from .docstring import clean_docstring
from .specs import FeatureSpec, FieldSpec, ModelSpec, is_model_class
from .type_analyzer import ConstraintSource, TypeInfo, TypeKind, analyze_type

__all__ = [
    "expand_model_tree",
    "extract_model",
    "resolve_field_alias",
]


def resolve_field_alias(field_name: str, field_info: FieldInfo) -> str:
    """Return the data-dict key for a Pydantic field.

    Prefers ``validation_alias``, falls back to ``alias``, then the
    Python field name. Only string aliases are supported; AliasPath
    and AliasChoices are ignored.
    """
    validation_alias = field_info.validation_alias
    if isinstance(validation_alias, str):
        return validation_alias
    alias = field_info.alias
    if isinstance(alias, str):
        return alias
    return field_name


def _merge_field_metadata(type_info: TypeInfo, field_info: FieldInfo) -> TypeInfo:
    """Merge constraints from field_info.metadata into TypeInfo.

    Pydantic strips the Annotated wrapper from some fields (non-optional,
    non-union) and moves the metadata to field_info.metadata. When this
    happens, analyze_type sees a bare type and misses the constraints.
    The two sets never overlap: field_info.metadata is empty when the
    Annotated wrapper survives in the annotation.
    """
    if not field_info.metadata:
        return type_info
    extra = tuple(ConstraintSource(None, m) for m in field_info.metadata)
    return dataclasses.replace(type_info, constraints=type_info.constraints + extra)


def _is_field_required(field_info: FieldInfo, type_info: TypeInfo) -> bool:
    """A field is required when it has no default and is not Optional."""
    has_default = (
        field_info.default is not PydanticUndefined
        or field_info.default_factory is not None
    )
    return not has_default and not type_info.is_optional


def _basemodel_bases(cls: type) -> list[type[BaseModel]]:
    """Return direct BaseModel bases, excluding BaseModel itself."""
    return [b for b in cls.__bases__ if is_model_class(b) and b is not BaseModel]


def _class_order(model_class: type[BaseModel]) -> list[type]:
    """Return MRO classes in documentation order, recursively.

    For single-inheritance: reversed MRO (base first, derived last).
    For multiple-inheritance: primary chain → self → mixins, where
    primary chain and each mixin are themselves recursively ordered.
    """
    bases = _basemodel_bases(model_class)

    if len(bases) <= 1:
        return [
            cls
            for cls in reversed(model_class.__mro__)
            if isinstance(cls, type)
            and issubclass(cls, BaseModel)
            and cls is not BaseModel
        ]

    primary = _class_order(bases[0])
    mixins = [cls for base in bases[1:] for cls in _class_order(base)]
    return primary + [model_class] + mixins


def _field_order(model_class: type[BaseModel]) -> list[str]:
    """Return model_fields keys in documentation order.

    Walks the class hierarchy recursively. At each level of multiple
    inheritance, the first base is the "primary chain" and the rest
    are "mixins." Primary chain and own fields come first, then mixin
    fields in declaration order. Single-inheritance levels use
    Pydantic's default reversed-MRO order.
    """
    valid_names = set(model_class.model_fields.keys())
    result: list[str] = []
    seen: set[str] = set()
    for cls in _class_order(model_class):
        for name in getattr(cls, "__annotations__", {}):
            if name not in seen and name in valid_names:
                result.append(name)
                seen.add(name)
    return result


def extract_model(
    model_class: type[BaseModel],
    *,
    entry_point: str | None = None,
) -> ModelSpec:
    """Extract model specification from a Pydantic model class."""
    field_info_map = model_class.model_fields
    ordered_keys = _field_order(model_class)

    fields: list[FieldSpec] = []
    for field_name in ordered_keys:
        field_info = field_info_map[field_name]
        output_name = resolve_field_alias(field_name, field_info)

        # Use field_info.annotation (resolved TypeVars) not get_type_hints
        annotation = field_info.annotation
        if annotation is None:
            continue

        type_info = _merge_field_metadata(analyze_type(annotation), field_info)

        fields.append(
            FieldSpec(
                name=output_name,
                type_info=type_info,
                description=field_info.description or type_info.description,
                is_required=_is_field_required(field_info, type_info),
            )
        )

    return ModelSpec(
        name=model_class.__name__,
        description=clean_docstring(model_class.__doc__),
        fields=fields,
        source_type=model_class,
        entry_point=entry_point,
        constraints=ModelConstraint.get_model_constraints(model_class),
    )


def expand_model_tree(
    spec: FeatureSpec,
    cache: dict[type, ModelSpec] | None = None,
) -> FeatureSpec:
    """Populate model references on MODEL-kind fields, recursively.

    Walks *spec*'s fields and sets ``field.model`` for fields whose type
    is a Pydantic model. Uses *cache* to reuse already-extracted ModelSpecs
    and detect shared references. Marks fields whose model creates a cycle
    in the ancestor chain with ``starts_cycle=True``.

    Mutates *spec* in place and returns it.
    """
    if cache is None:
        cache = {}
    if isinstance(spec, ModelSpec) and spec.source_type is not None:
        cache[spec.source_type] = spec
    ancestors = frozenset({spec.source_type}) if spec.source_type else frozenset()
    _expand_fields(spec.fields, cache, ancestors)
    return spec


def _expand_fields(
    fields: list[FieldSpec],
    cache: dict[type, ModelSpec],
    ancestors: frozenset[type],
) -> None:
    """Recursive helper for expand_model_tree.

    Cache insertion happens before recursion — cycle detection depends
    on the ancestor's ModelSpec being in the cache when the back-edge
    is encountered.
    """
    for field_spec in fields:
        ti = field_spec.type_info
        source = ti.source_type
        if ti.kind == TypeKind.UNION:
            # Union fields have no single model to recurse into.
            # The field row appears in the output; skip inline expansion.
            continue
        if ti.kind != TypeKind.MODEL or source is None:
            continue

        if source in ancestors:
            # Cycle: reuse existing spec, mark the edge
            field_spec.model = cache.get(source)
            field_spec.starts_cycle = True
        elif source in cache:
            # Shared reference: reuse, not a cycle
            field_spec.model = cache[source]
        else:
            sub_spec = extract_model(source)
            cache[source] = sub_spec  # insert BEFORE recursing
            field_spec.model = sub_spec
            _expand_fields(sub_spec.fields, cache, ancestors | {source})
