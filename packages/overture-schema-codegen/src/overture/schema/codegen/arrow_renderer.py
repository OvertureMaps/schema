"""Arrow schema renderer for Pydantic models."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from types import MappingProxyType
from typing import NamedTuple

import pyarrow as pa  # type: ignore[import-untyped]

from .extraction.model_extraction import extract_model
from .extraction.specs import FieldSpec, ModelSpec, UnionSpec
from .extraction.type_analyzer import TypeInfo, TypeKind
from .extraction.type_registry import PRIMITIVE_TYPES, get_type_mapping

log = logging.getLogger(__name__)

__all__ = [
    "field_spec_to_arrow",
    "merge_model_variants",
    "model_spec_to_arrow_schema",
    "type_info_to_arrow",
    "union_spec_to_arrow_schema",
]


def _build_arrow_factories() -> MappingProxyType[str, pa.DataType]:
    """Build Arrow type lookup from the type registry's arrow mappings.

    Collects every non-None arrow name from PRIMITIVE_TYPES and resolves
    it via getattr(pa, name)() at import time. Fails fast if a registry
    entry names a nonexistent pyarrow factory.
    """
    factories: dict[str, pa.DataType] = {}
    for mapping in PRIMITIVE_TYPES.values():
        name = mapping.arrow
        if name is None or name in factories:
            continue
        factory = getattr(pa, name, None)
        if factory is None:
            raise AttributeError(f"pyarrow has no factory {name!r}")
        factories[name] = factory()
    return MappingProxyType(factories)


_ARROW_FACTORIES = _build_arrow_factories()

_DEFAULT_ARROW_TYPE = _ARROW_FACTORIES["utf8"]

# Types needing construction beyond a simple pa.<name>() factory.
_CUSTOM_ARROW_TYPES: MappingProxyType[str, pa.DataType] = MappingProxyType(
    {
        "BBox": pa.struct(
            [
                pa.field("xmin", pa.float64()),
                pa.field("ymin", pa.float64()),
                pa.field("xmax", pa.float64()),
                pa.field("ymax", pa.float64()),
            ]
        ),
    }
)


def _model_to_struct(
    model_class: type,
    ancestors: frozenset[type],
) -> pa.DataType:
    """Convert a BaseModel subclass to a pa.StructType."""
    if model_class in ancestors:
        log.warning("Cycle detected at %s, substituting utf8", model_class.__name__)
        return pa.utf8()

    spec = extract_model(model_class)
    child_ancestors = ancestors | {model_class}
    fields = [field_spec_to_arrow(f, child_ancestors) for f in spec.fields]
    return pa.struct(fields)


def type_info_to_arrow(
    type_info: TypeInfo,
    ancestors: frozenset[type] = frozenset(),
) -> pa.DataType:
    """Convert a TypeInfo to a PyArrow DataType."""
    if type_info.is_dict:
        if type_info.dict_key_type is None or type_info.dict_value_type is None:
            raise ValueError(
                f"Dict TypeInfo missing key or value type: {type_info.base_type}"
            )
        key_type = type_info_to_arrow(type_info.dict_key_type, ancestors)
        value_type = type_info_to_arrow(type_info.dict_value_type, ancestors)
        return pa.map_(key_type, value_type)

    if type_info.kind == TypeKind.UNION:
        if not type_info.union_members:
            raise ValueError(f"Union TypeInfo has no members: {type_info.base_type}")
        arrow_type = merge_model_variants(type_info.union_members)
    elif type_info.kind == TypeKind.MODEL:
        if type_info.source_type is None:
            raise ValueError(
                f"MODEL TypeInfo missing source_type: {type_info.base_type}"
            )
        arrow_type = _model_to_struct(type_info.source_type, ancestors)
    elif type_info.kind in (TypeKind.ENUM, TypeKind.LITERAL):
        arrow_type = pa.utf8()
    elif type_info.base_type in _CUSTOM_ARROW_TYPES:
        arrow_type = _CUSTOM_ARROW_TYPES[type_info.base_type]
    else:
        mapping = get_type_mapping(type_info.base_type)
        if mapping and mapping.arrow:
            arrow_type = _ARROW_FACTORIES[mapping.arrow]
        else:
            log.warning(
                "Unknown Arrow type for %r, falling back to utf8",
                type_info.base_type,
            )
            arrow_type = _DEFAULT_ARROW_TYPE

    if type_info.is_list:
        return pa.list_(arrow_type)

    return arrow_type


def field_spec_to_arrow(
    field_spec: FieldSpec,
    ancestors: frozenset[type] = frozenset(),
) -> pa.Field:
    """Convert a FieldSpec to a PyArrow Field."""
    arrow_type = type_info_to_arrow(field_spec.type_info, ancestors)
    nullable = field_spec.type_info.is_optional
    metadata = (
        {b"description": field_spec.description.encode()}
        if field_spec.description is not None
        else None
    )
    return pa.field(field_spec.name, arrow_type, nullable=nullable, metadata=metadata)


def _build_schema_metadata(
    version: str | None,
    entry_point: str | None,
) -> dict[bytes, bytes] | None:
    """Build schema-level metadata dict, or None if empty."""
    metadata: dict[bytes, bytes] = {}
    if version:
        metadata[b"overture-schema.version"] = version.encode()
    if entry_point is not None:
        metadata[b"model"] = entry_point.encode()
    return metadata or None


def model_spec_to_arrow_schema(
    model_spec: ModelSpec,
    *,
    version: str | None = None,
) -> pa.Schema:
    """Convert a ModelSpec to a PyArrow Schema."""
    fields = [field_spec_to_arrow(f) for f in model_spec.fields]
    return pa.schema(
        fields, metadata=_build_schema_metadata(version, model_spec.entry_point)
    )


def union_spec_to_arrow_schema(
    union_spec: UnionSpec,
    *,
    version: str | None = None,
) -> pa.Schema:
    """Convert a UnionSpec to a PyArrow Schema by merging member variants."""
    merged_struct = merge_model_variants(union_spec.members)
    return pa.schema(
        list(merged_struct),
        metadata=_build_schema_metadata(version, union_spec.entry_point),
    )


class _NumericRank(NamedTuple):
    width: int
    is_float: bool


_NUMERIC_RANKS: MappingProxyType[pa.DataType, _NumericRank] = MappingProxyType(
    {
        pa.int8(): _NumericRank(8, False),
        pa.int16(): _NumericRank(16, False),
        pa.int32(): _NumericRank(32, False),
        pa.int64(): _NumericRank(64, False),
        pa.uint8(): _NumericRank(8, False),
        pa.uint16(): _NumericRank(16, False),
        pa.uint32(): _NumericRank(32, False),
        pa.uint64(): _NumericRank(64, False),
        pa.float32(): _NumericRank(32, True),
        pa.float64(): _NumericRank(64, True),
    }
)

# When mixing signed and unsigned at the same width, promote to the next
# wider signed type.  Width 64 maps to int64 -- lossy for large uint64
# values, but Arrow has no int128 and this matches Spark/Parquet behavior.
_WIDER_SIGNED: MappingProxyType[int, pa.DataType] = MappingProxyType(
    {
        8: pa.int16(),
        16: pa.int32(),
        32: pa.int64(),
        64: pa.int64(),
    }
)


def _promote_arrow_types(a: pa.DataType, b: pa.DataType) -> pa.DataType:
    """Promote two Arrow types to a common wider type.

    Rules:
    - Same type returns unchanged.
    - Mixing int and float promotes to float64.
    - Mixing signed and unsigned promotes to the next wider signed int.
    - Otherwise the wider type wins.

    Raises ValueError for non-numeric type conflicts (struct, list, binary)
    where no promotion path exists.
    """
    if a == b:
        return a

    rank_a = _NUMERIC_RANKS.get(a)
    rank_b = _NUMERIC_RANKS.get(b)
    if rank_a is None or rank_b is None:
        raise ValueError(f"Cannot promote non-numeric Arrow types {a} and {b}")

    if rank_a.is_float != rank_b.is_float:
        return pa.float64()

    if pa.types.is_unsigned_integer(a) != pa.types.is_unsigned_integer(b):
        return _WIDER_SIGNED[max(rank_a.width, rank_b.width)]

    return a if rank_a.width >= rank_b.width else b


def merge_model_variants(model_classes: Sequence[type]) -> pa.StructType:
    """Merge multiple BaseModel variants into a single Arrow struct.

    Fields present in all variants keep their promoted type.
    Fields absent from some variants become nullable.
    """
    variant_fields: list[dict[str, pa.Field]] = []
    for cls in model_classes:
        spec = extract_model(cls)
        fields_dict = {f.name: field_spec_to_arrow(f) for f in spec.fields}
        variant_fields.append(fields_dict)

    all_names = dict.fromkeys(
        name for fields_dict in variant_fields for name in fields_dict
    )

    merged: list[pa.Field] = []
    for name in all_names:
        present_in = [fd for fd in variant_fields if name in fd]
        absent_from_some = len(present_in) < len(variant_fields)

        first_field = present_in[0][name]
        result_type = first_field.type
        for fd in present_in[1:]:
            result_type = _promote_arrow_types(result_type, fd[name].type)

        nullable = absent_from_some or any(fd[name].nullable for fd in present_in)
        metadata = next(
            (fd[name].metadata for fd in present_in if fd[name].metadata), None
        )
        merged.append(pa.field(name, result_type, nullable=nullable, metadata=metadata))

    return pa.struct(merged)
