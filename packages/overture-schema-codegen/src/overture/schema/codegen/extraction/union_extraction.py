"""Union extraction and discriminator handling."""

from __future__ import annotations

from typing import Annotated, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from overture.schema.system.feature import resolve_discriminator_field_name

from .model_extraction import extract_model, resolve_field_alias
from .specs import AnnotatedField, UnionSpec, is_model_class
from .type_analyzer import TypeInfo, TypeKind, analyze_type, single_literal_value

__all__ = ["extract_discriminator", "extract_union"]


def _find_common_base(members: list[type[BaseModel]]) -> type[BaseModel]:
    """Find the most-derived common BaseModel ancestor of all members."""
    if not members:
        raise ValueError("Cannot find common base of empty members list")
    filtered_mros = [
        [c for c in cls.__mro__ if is_model_class(c) and c is not BaseModel]
        for cls in members
    ]
    common = set(filtered_mros[0])
    for mro in filtered_mros[1:]:
        common &= set(mro)
    if not common:
        raise ValueError(
            f"No common BaseModel ancestor for {[m.__name__ for m in members]}"
        )

    def max_mro_index(cls: type) -> int:
        return max(mro.index(cls) for mro in filtered_mros)

    return min(common, key=max_mro_index)


def _find_field_by_alias(model: type[BaseModel], alias: str) -> FieldInfo | None:
    """Find a field in model_fields by alias-resolved name."""
    direct = model.model_fields.get(alias)
    if direct is not None:
        return direct
    for py_name, fi in model.model_fields.items():
        if resolve_field_alias(py_name, fi) == alias:
            return fi
    return None


def extract_discriminator(
    annotation: object,
    members: list[type[BaseModel]],
) -> tuple[str | None, dict[str, type[BaseModel]] | None]:
    """Extract discriminator field name and value-to-type mapping."""
    if get_origin(annotation) is not Annotated:
        return None, None

    disc_field_name: str | None = None
    for metadata in get_args(annotation)[1:]:
        if isinstance(metadata, FieldInfo):
            disc_field_name = resolve_discriminator_field_name(metadata.discriminator)
            if disc_field_name is not None:
                break

    if disc_field_name is None:
        return None, None

    mapping: dict[str, type[BaseModel]] = {}
    for member in members:
        field_info = _find_field_by_alias(member, disc_field_name)
        if field_info and field_info.annotation is not None:
            lit_val = single_literal_value(field_info.annotation)
            if lit_val is not None:
                mapping[str(lit_val)] = member

    return disc_field_name, mapping or None


_TypeShape = tuple[str, TypeKind, bool, int]
_FieldKey = tuple[str, _TypeShape]


def _type_shape(ti: TypeInfo) -> _TypeShape:
    """Structural shape for dedup -- excludes source_type which varies across members."""
    return (ti.base_type, ti.kind, ti.is_optional, ti.list_depth)


def extract_union(
    name: str,
    annotation: object,
    *,
    entry_point: str | None = None,
) -> UnionSpec:
    """Extract a UnionSpec from a discriminated union type alias."""
    ti = analyze_type(annotation)
    if ti.kind != TypeKind.UNION or ti.union_members is None:
        raise TypeError(f"{name} is not a union type alias")

    members = list(ti.union_members)
    common_base = _find_common_base(members)

    base_spec = extract_model(common_base)
    shared_field_names = {f.name for f in base_spec.fields}

    member_specs = [(m, extract_model(m)) for m in members]

    annotated_fields: list[AnnotatedField] = []

    # Shared fields first (from common base)
    for fs in base_spec.fields:
        annotated_fields.append(AnnotatedField(field_spec=fs, variant_sources=None))

    # Variant-specific fields: collect by (name, type identity) for dedup
    seen: dict[_FieldKey, AnnotatedField] = {}

    for member_cls, member_spec in member_specs:
        for fs in member_spec.fields:
            if fs.name in shared_field_names:
                continue
            key = (fs.name, _type_shape(fs.type_info))
            existing = seen.get(key)
            prior_sources = existing.variant_sources or () if existing else ()
            seen[key] = AnnotatedField(
                field_spec=fs,
                variant_sources=(*prior_sources, member_cls.__name__),
            )

    annotated_fields.extend(seen.values())

    disc_field, disc_mapping = extract_discriminator(annotation, members)

    return UnionSpec(
        name=name,
        description=ti.description,
        annotated_fields=annotated_fields,
        members=members,
        discriminator_field=disc_field,
        discriminator_mapping=disc_mapping,
        source_annotation=annotation,
        common_base=common_base,
        entry_point=entry_point,
    )
