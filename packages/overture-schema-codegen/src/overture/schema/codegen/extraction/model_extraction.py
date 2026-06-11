"""Pydantic model extraction into `ModelSpec`."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from overture.schema.system.model_constraint import ModelConstraint

from .docstring import clean_docstring
from .field import (
    ConstraintSource,
    FieldShape,
    ModelRef,
    UnionRef,
)
from .specs import FieldSpec, ModelSpec, is_model_class
from .type_analyzer import (
    ModelResolver,
    UnionResolver,
    analyze_type,
    attach_constraints,
    unwrap_list,
)

__all__ = [
    "extract_model",
    "resolve_field_alias",
]


def resolve_field_alias(field_name: str, field_info: FieldInfo) -> str:
    """Return the data-dict key for a Pydantic field.

    Prefers `validation_alias`, falls back to `alias`, then the
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


def _is_field_required(field_info: FieldInfo, is_optional: bool) -> bool:
    """Determine whether a field is required (no default and not Optional)."""
    has_default = (
        field_info.default is not PydanticUndefined
        or field_info.default_factory is not None
    )
    return not has_default and not is_optional


def _attach_field_metadata(shape: FieldShape, field_info: FieldInfo) -> FieldShape:
    """Merge constraints from `field_info.metadata` onto *shape*.

    Pydantic strips the outermost Annotated wrapper from some fields
    (non-optional, non-union) and moves its metadata to
    `field_info.metadata`. When that happens `analyze_type` sees a bare
    type and misses those constraints. They anchor at the topmost
    constraint-bearing layer, so we route them through
    `attach_constraints` so that length-constraint wrapping applies here
    just as it does during normal annotation unwrapping.
    """
    if not field_info.metadata:
        return shape
    extra = tuple(ConstraintSource(None, None, m) for m in field_info.metadata)
    return attach_constraints(shape, extra)


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
            if issubclass(cls, BaseModel) and cls is not BaseModel
        ]

    primary = _class_order(bases[0])
    mixins = [cls for base in bases[1:] for cls in _class_order(base)]
    return primary + [model_class] + mixins


def _field_order(model_class: type[BaseModel]) -> list[str]:
    """Return `model_fields` keys in documentation order.

    Walks the class hierarchy recursively. At each level of multiple
    inheritance, the first base is the primary chain and the rest are
    mixins. Primary chain and own fields come first, then mixin fields
    in declaration order. Single-inheritance levels use Pydantic's
    default reversed-MRO order.
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
    partitions: Mapping[str, str] | None = None,
) -> ModelSpec:
    """Extract a fully-resolved `ModelSpec` from a Pydantic model class.

    Recurses into sub-models and unions, producing `ModelRef` /
    `UnionRef` terminals with their specs resolved. Cycles in the
    model graph (a field whose source type is an ancestor on the
    current extraction stack) produce a `ModelRef` pointing at the
    in-progress ancestor spec with `starts_cycle=True` so consumers
    stop recursion at the back-edge.
    """
    return _extract_model_recursive(
        model_class,
        entry_point=entry_point,
        partitions=partitions or {},
        cache={},
        ancestors=frozenset(),
    )


def _extract_model_recursive(
    model_class: type[BaseModel],
    *,
    entry_point: str | None,
    partitions: Mapping[str, str],
    cache: dict[type, ModelSpec],
    ancestors: frozenset[type],
) -> ModelSpec:
    """Inner recursive helper for `extract_model`.

    Inserts the (partial) `ModelSpec` into `cache` before populating
    its fields so cycles can find it. `ancestors` is the set of types
    currently on the recursion stack -- a sub-field whose source type
    appears there is a back-edge and gets `starts_cycle=True`.
    """
    spec = ModelSpec(
        name=model_class.__name__,
        description=clean_docstring(model_class.__doc__),
        fields=[],
        source_type=model_class,
        entry_point=entry_point,
        partitions=partitions,
        constraints=ModelConstraint.get_model_constraints(model_class),
    )
    cache[model_class] = spec
    descendant_ancestors = ancestors | {model_class}

    model_resolver, union_resolver = _make_resolvers(cache, descendant_ancestors)

    fields: list[FieldSpec] = []
    for field_name in _field_order(model_class):
        field_info = model_class.model_fields[field_name]
        annotation = field_info.annotation
        if annotation is None:
            continue
        shape, is_optional, ti_description = analyze_type(
            annotation,
            model_resolver=model_resolver,
            union_resolver=union_resolver,
        )
        shape = _attach_field_metadata(shape, field_info)
        fields.append(
            FieldSpec(
                name=resolve_field_alias(field_name, field_info),
                shape=shape,
                description=field_info.description or ti_description,
                is_required=_is_field_required(field_info, is_optional),
                is_optional=is_optional,
            )
        )

    spec.fields = fields
    return spec


def _make_resolvers(
    cache: dict[type, ModelSpec],
    ancestors: frozenset[type],
) -> tuple[ModelResolver, UnionResolver]:
    """Build the resolvers that recursively extract sub-models / sub-unions.

    `cache` shares already-extracted sub-specs across a single
    extraction so sub-models referenced more than once share a
    `ModelSpec`. `ancestors` carries the recursion stack for cycle
    detection -- a back-edge produces a `ModelRef` pointing at the
    in-progress ancestor spec with `starts_cycle=True`.
    """

    def resolve_model(cls: type[BaseModel]) -> ModelRef:
        if cls in ancestors:
            return ModelRef(model=cache[cls], starts_cycle=True)
        cached = cache.get(cls)
        if cached is not None:
            return ModelRef(model=cached)
        sub_spec = _extract_model_recursive(
            cls,
            entry_point=None,
            partitions={},
            cache=cache,
            ancestors=ancestors,
        )
        return ModelRef(model=sub_spec)

    def resolve_union(
        annotation: object,
        members: tuple[type[BaseModel], ...],
        _description: str | None,
    ) -> UnionRef:
        # Late import: extract_union calls back into extract_model for
        # member classes. A module-level import would be a cycle.
        from .union_extraction import extract_union

        # Recover the union alias name: `analyze_type` reaches the
        # union via `members[0].__name__` when the alias name is lost
        # (plain `Foo = Annotated[...]` doesn't preserve it pre-PEP-695).
        # Convention: members extend `<Alias>Base`.
        placeholder = members[0].__name__ if members else ""
        sub_union = extract_union(placeholder, unwrap_list(annotation))
        return UnionRef(union=sub_union)

    return resolve_model, resolve_union
