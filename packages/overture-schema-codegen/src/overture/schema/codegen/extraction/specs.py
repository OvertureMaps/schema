"""Data types for extracted specifications."""

from __future__ import annotations

import functools
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, TypeAlias, TypeGuard

from annotated_types import Interval
from pydantic import BaseModel, RootModel

from overture.schema.system.discovery.tag import get_values_for_key
from overture.schema.system.model_constraint import ModelConstraint

from .field import FieldShape
from .type_analyzer import capture_union_members

__all__ = [
    "AnnotatedField",
    "EnumMemberSpec",
    "EnumSpec",
    "ModelSpec",
    "FieldSpec",
    "MemberSpec",
    "RecordSpec",
    "NewTypeSpec",
    "NumericSpec",
    "PydanticTypeSpec",
    "SupplementarySpec",
    "TypeIdentity",
    "filter_model_classes",
    "is_model_class",
    "is_pydantic_sourced",
    "is_rootmodel",
    "is_union_alias",
    "partitions_from_tags",
]


def partitions_from_tags(tags: frozenset[str]) -> dict[str, str]:
    """Map registry tags to Hive partition columns for a feature.

    Today populated only from `overture:theme=<name>`; the value object is
    a generic name -> value map so additional partition keys (e.g. release
    version) can be added without changing the surrounding pipeline.
    """
    theme = next(iter(get_values_for_key(tags, "overture:theme")), None)
    return {"theme": theme} if theme is not None else {}


@dataclass(frozen=True, eq=False)
class TypeIdentity:
    """Unique identity for a type in the codegen system.

    Pairs a unique Python object (class, NewType callable, or union
    annotation) with its display name. Equality and hashing delegate
    to `obj` identity so registry lookups work regardless of how
    the display name was derived.
    """

    obj: object
    name: str

    @classmethod
    def of(cls, obj: object) -> TypeIdentity:
        """Derive a TypeIdentity from a named object (class, NewType, etc.)."""
        name = getattr(obj, "__name__", None)
        if name is None:
            raise TypeError(f"Cannot derive TypeIdentity from {obj!r}: no __name__")
        return cls(obj, name)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TypeIdentity) and self.obj is other.obj

    def __hash__(self) -> int:
        return id(self.obj)

    @property
    def module(self) -> str:
        """Source module of the underlying object, or empty string."""
        return getattr(self.obj, "__module__", "")


class _SourceTypeIdentityMixin:
    """Mixin providing `identity` from `source_type` and `name`.

    Shared by EnumSpec, RecordSpec, NewTypeSpec, and PydanticTypeSpec --
    each has a `source_type` (the Python class/callable) and a `name`.
    UnionSpec uses `source_annotation` instead, so it defines its
    own `identity`.
    """

    source_type: object | None
    name: str

    @property
    def identity(self) -> TypeIdentity:
        if self.source_type is None:
            raise ValueError(f"Cannot derive identity for {self.name}: no source_type")
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
    """Specification for a model field: header metadata plus structural shape.

    `shape` is the full `FieldShape` tree, including any sub-model
    (`ModelRef`) and sub-union (`UnionRef`) references already
    resolved during extraction.
    """

    name: str
    shape: FieldShape
    description: str | None = None
    is_required: bool = True
    is_optional: bool = False


@dataclass
class RecordSpec(_SourceTypeIdentityMixin):
    """Specification for a Pydantic model."""

    name: str
    description: str | None
    fields: list[FieldSpec] = field(default_factory=list)
    source_type: type[BaseModel] | None = None
    entry_point: str | None = None
    partitions: Mapping[str, str] = field(default_factory=dict)
    constraints: tuple[ModelConstraint, ...] = ()


@dataclass
class AnnotatedField:
    """A FieldSpec paired with union variant provenance."""

    field_spec: FieldSpec
    variant_sources: tuple[type[BaseModel], ...] | None


@dataclass
class MemberSpec:
    """A union member's class paired with its extracted `RecordSpec`.

    `extract_union` already runs `extract_model` on every member to
    build the merged `annotated_fields`; retaining the result here lets
    consumers (check builder, base-row generator) reuse it instead of
    re-extracting the same subtree.
    """

    member_cls: type[BaseModel]
    spec: RecordSpec


# eq=False: contains mutable lists and a cached_property, so the
# dataclass-generated __eq__ would compare by value over mutable fields and
# __hash__ would be disabled (unhashable). Consumers key on object identity.
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
    member_specs: list[MemberSpec] = field(default_factory=list)
    source_type: type[BaseModel] | None = field(default=None, init=False)
    entry_point: str | None = None
    partitions: Mapping[str, str] = field(default_factory=dict)
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
    """Specification for a NewType.

    `shape` is the underlying shape -- i.e. the `inner` of the
    NewType's own `NewTypeShape` wrapper, with the wrapper stripped
    so the NewType isn't a self-reference on its own page.
    """

    name: str
    description: str | None
    shape: FieldShape
    source_type: object | None = None


@dataclass
class NumericSpec:
    """Extracted specification for a numeric type."""

    name: str
    description: str | None
    bounds: Interval = field(default_factory=Interval)
    float_bits: int | None = None


@dataclass
class PydanticTypeSpec(_SourceTypeIdentityMixin):
    """Specification for a Pydantic built-in type (HttpUrl, EmailStr, etc.)."""

    name: str
    description: str | None
    source_type: type
    source_module: str

    @property
    def docs_url(self) -> str:
        """Pydantic documentation URL for this type."""
        return (
            f"https://docs.pydantic.dev/latest/api/{self.source_module}"
            f"/#pydantic.{self.source_module}.{self.name}"
        )


ModelSpec: TypeAlias = RecordSpec | UnionSpec
"""A model is one record, or a tagged union of records.

The top-level type passed through the extraction pipeline. Consumers
narrow with `isinstance` when an arm-specific attribute is needed
(e.g. `UnionSpec.discriminator_field`).
"""

SupplementarySpec = EnumSpec | NewTypeSpec | RecordSpec | PydanticTypeSpec
"""Supplementary types referenced by models.

Excludes NumericSpec and geometry types, which are extracted
separately via dedicated functions.
"""


def is_pydantic_sourced(source_type: type | None) -> bool:
    """Check whether *source_type* originates from the `pydantic` package."""
    return getattr(source_type, "__module__", "").startswith("pydantic")


def is_model_class(obj: object) -> TypeGuard[type[BaseModel]]:
    """Check whether *obj* is a concrete BaseModel subclass (not a type alias)."""
    return isinstance(obj, type) and issubclass(obj, BaseModel)


def is_rootmodel(obj: object) -> TypeGuard[type[RootModel]]:
    """Check whether *obj* is a `RootModel` subclass.

    A RootModel is a `BaseModel` (so `is_model_class` also accepts it) but
    serializes as its bare root value rather than a struct of fields. It
    has no record structure to extract, so callers treat it apart from a
    plain model class.
    """
    return isinstance(obj, type) and issubclass(obj, RootModel)


def is_union_alias(obj: object) -> bool:
    """Check whether *obj* is a discriminated union type alias of BaseModel subclasses."""
    return capture_union_members(obj) is not None


def filter_model_classes(models: dict[Any, Any]) -> list[type[BaseModel]]:
    """Filter discovered models to concrete BaseModel subclasses.

    Excludes type aliases (like discriminated unions) and non-class entries.
    """
    return [v for v in models.values() if is_model_class(v)]
