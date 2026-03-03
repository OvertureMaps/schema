"""Data types for extracted specifications."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeGuard, runtime_checkable

from annotated_types import Interval
from pydantic import BaseModel

from overture.schema.system.model_constraint import ModelConstraint

from .type_analyzer import TypeInfo, TypeKind, UnsupportedUnionError, analyze_type

__all__ = [
    "AnnotatedField",
    "EnumMemberSpec",
    "EnumSpec",
    "FeatureSpec",
    "FieldSpec",
    "ModelSpec",
    "NewTypeSpec",
    "PrimitiveSpec",
    "SupplementarySpec",
    "TypeIdentity",
    "filter_model_classes",
    "is_model_class",
    "is_union_alias",
]


@dataclass(frozen=True, eq=False)
class TypeIdentity:
    """Unique identity for a type in the codegen system.

    Pairs a unique Python object (class, NewType callable, or union
    annotation) with its display name. Equality and hashing delegate
    to ``obj`` identity so registry lookups work regardless of how
    the display name was derived.
    """

    obj: object
    name: str

    @classmethod
    def of(cls, obj: object) -> TypeIdentity:
        """Derive a TypeIdentity from a named object (class, NewType, etc.)."""
        assert obj is not None
        return cls(obj, obj.__name__)  # type: ignore[attr-defined]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TypeIdentity) and self.obj is other.obj

    def __hash__(self) -> int:
        return id(self.obj)


class _SourceTypeIdentityMixin:
    """Mixin providing ``identity`` from ``source_type`` and ``name``.

    Shared by EnumSpec, ModelSpec, and NewTypeSpec -- each has a
    ``source_type`` (the Python class/callable) and a ``name``.
    UnionSpec uses ``source_annotation`` instead, so it defines its
    own ``identity``.
    """

    source_type: object | None
    name: str

    @property
    def identity(self) -> TypeIdentity:
        assert self.source_type is not None
        return TypeIdentity(self.source_type, self.name)


@dataclass
class EnumMemberSpec:
    """Specification for an enum member."""

    name: str
    value: str
    description: str | None


@dataclass
class EnumSpec(_SourceTypeIdentityMixin):
    """Specification for an Enum class."""

    name: str
    description: str | None
    members: list[EnumMemberSpec] = field(default_factory=list)
    source_type: type | None = None


@dataclass
class FieldSpec:
    """Specification for a model field."""

    name: str
    type_info: TypeInfo
    description: str | None
    is_required: bool
    model: ModelSpec | None = None
    starts_cycle: bool = False


@runtime_checkable
class FeatureSpec(Protocol):
    """Shared interface for feature-level specs (ModelSpec, UnionSpec)."""

    name: str
    description: str | None
    source_type: type[BaseModel] | None
    entry_point: str | None
    constraints: tuple[ModelConstraint, ...]

    @property
    def fields(self) -> list[FieldSpec]: ...

    @property
    def identity(self) -> TypeIdentity: ...


@dataclass
class ModelSpec(_SourceTypeIdentityMixin):
    """Specification for a Pydantic model."""

    name: str
    description: str | None
    fields: list[FieldSpec] = field(default_factory=list)
    source_type: type[BaseModel] | None = None
    entry_point: str | None = None
    constraints: tuple[ModelConstraint, ...] = ()


@dataclass
class AnnotatedField:
    """A FieldSpec paired with union variant provenance."""

    field_spec: FieldSpec
    variant_sources: tuple[str, ...] | None


# eq=False: contains mutable lists and a cached_property, so
# dataclass-generated __eq__ would be unreliable.
@dataclass(eq=False)
class UnionSpec:
    """Specification for a discriminated union type alias."""

    name: str
    description: str | None
    annotated_fields: list[AnnotatedField]
    members: list[type[BaseModel]]
    discriminator_field: str | None
    discriminator_mapping: dict[str, type[BaseModel]] | None
    source_annotation: object
    common_base: type[BaseModel]
    source_type: type[BaseModel] | None = field(default=None, init=False)
    entry_point: str | None = None
    constraints: tuple[ModelConstraint, ...] = ()

    @functools.cached_property
    def fields(self) -> list[FieldSpec]:
        """Plain field list for tree expansion and supplementary collection."""
        return [af.field_spec for af in self.annotated_fields]

    @property
    def identity(self) -> TypeIdentity:
        return TypeIdentity(self.source_annotation, self.name)


@dataclass
class NewTypeSpec(_SourceTypeIdentityMixin):
    """Specification for a NewType."""

    name: str
    description: str | None
    type_info: TypeInfo
    source_type: object | None = None


@dataclass
class PrimitiveSpec:
    """Extracted specification for a numeric primitive type."""

    name: str
    description: str | None
    bounds: Interval = field(default_factory=Interval)
    float_bits: int | None = None


SupplementarySpec = EnumSpec | NewTypeSpec | ModelSpec
"""Non-feature types referenced by feature models.

Excludes PrimitiveSpec and geometry types, which are extracted
separately via dedicated functions.
"""


def is_model_class(obj: object) -> TypeGuard[type[BaseModel]]:
    """Check whether *obj* is a concrete BaseModel subclass (not a type alias)."""
    return isinstance(obj, type) and issubclass(obj, BaseModel)


def is_union_alias(obj: object) -> bool:
    """Check whether *obj* is a discriminated union type alias of BaseModel subclasses."""
    try:
        ti = analyze_type(obj)
    except (TypeError, UnsupportedUnionError):
        return False
    return ti.kind == TypeKind.UNION


def filter_model_classes(models: dict[Any, Any]) -> list[type[BaseModel]]:
    """Filter discovered models to concrete BaseModel subclasses.

    Excludes type aliases (like discriminated unions) and non-class entries.
    """
    return [v for v in models.values() if is_model_class(v)]
