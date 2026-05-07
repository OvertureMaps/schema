"""Build StructType schema source from FeatureSpec field trees."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..extraction.field import (
    AnyScalar,
    ArrayOf,
    FieldShape,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    Scalar,
    UnionRef,
)
from ..extraction.field_walk import terminal_scalar
from ..extraction.specs import FeatureSpec, FieldSpec, UnionSpec
from ..extraction.type_registry import get_type_mapping

__all__ = [
    "SHARED_TYPE_REFS",
    "SchemaField",
    "build_schema",
    "spark_type_rank",
]

# Types whose base_type name maps to a _schema_structs.py StructType constant.
# Reserved for types the codegen cannot walk (BBox is a plain class, not a
# Pydantic BaseModel).  Pydantic BaseModels are inlined.
SHARED_TYPE_REFS: dict[str, str] = {
    "BBox": "BBOX_STRUCT",
}

# Literal and Enum fields both serialize as strings in Parquet.
_STRING_FALLBACK = "StringType()"


@dataclass(frozen=True, slots=True)
class SchemaField:
    """One field in the generated StructType.

    Parameters
    ----------
    name
        Column name.
    type_expr
        Spark type expression string (e.g. `"StringType()"`) or
        a `_schema_structs.py` constant name.
    """

    name: str
    type_expr: str


def _spark_for_base(base_type: str, source_type: type | None) -> str:
    """Return a Spark type expression for a primitive base type.

    Tries `base_type` first, then falls back to `source_type.__name__`.
    Returns `StringType()` when neither maps to a known Spark type.
    """
    mapping = get_type_mapping(base_type)
    if mapping is not None and mapping.spark is not None:
        return mapping.spark
    if source_type is not None:
        fallback = get_type_mapping(source_type.__name__)
        if fallback is not None and fallback.spark is not None:
            return fallback.spark
    return _STRING_FALLBACK


def _spark_for_scalar(scalar: Scalar) -> str:
    """Map a `Scalar` variant to a Spark type expression.

    `LiteralScalar` and `AnyScalar` serialize as strings. `Primitive`
    scalars look up the type registry; enum primitives and BBox short-
    circuit to strings / shared constants before the registry.
    """
    if isinstance(scalar, (LiteralScalar, AnyScalar)):
        return _STRING_FALLBACK
    if scalar.base_type in SHARED_TYPE_REFS:
        return SHARED_TYPE_REFS[scalar.base_type]
    if (
        scalar.source_type is not None
        and isinstance(scalar.source_type, type)
        and issubclass(scalar.source_type, Enum)
    ):
        return _STRING_FALLBACK
    return _spark_for_base(scalar.base_type, scalar.source_type)


# Spark numeric type widening precedence (higher rank = wider type).
_SPARK_TYPE_WIDENING: dict[str, int] = {
    "IntegerType()": 0,
    "LongType()": 1,
    "DoubleType()": 2,
}


def spark_type_rank(field_spec: FieldSpec) -> int:
    """Return a widening rank for the field's resolved Spark type.

    Fields with a higher rank are preferred when deduplicating union
    members by name. Non-numeric types return -1 (no widening).
    """
    scalar = terminal_scalar(field_spec.shape)
    if not isinstance(scalar, Primitive):
        return -1
    expr = _spark_for_base(scalar.base_type, scalar.source_type)
    return _SPARK_TYPE_WIDENING.get(expr, -1)


def _deduplicate_by_name(fields: list[FieldSpec]) -> list[FieldSpec]:
    """Keep one FieldSpec per name, widening the Spark type on conflict.

    Union annotated_fields may contain the same field name with different
    type shapes (e.g. `value` as uint8 in one variant and float64 in
    another). Parquet stores one column per name, so the schema needs
    exactly one entry. When two fields share a name, the one with the
    wider Spark type wins (matching Parquet's type-widening behavior).
    """
    seen: dict[str, FieldSpec] = {}
    for f in fields:
        existing = seen.get(f.name)
        if existing is None or spark_type_rank(f) > spark_type_rank(existing):
            seen[f.name] = f
    return list(seen.values())


def _struct_type_expr(fields: list[FieldSpec]) -> str:
    """Build an inline `StructType([...])` expression from a list of fields."""
    parts = [
        f'StructField("{f.name}", {_shape_to_spark(f.shape)}, True)' for f in fields
    ]
    return f"StructType([{', '.join(parts)}])"


def _shape_to_spark(shape: FieldShape) -> str:
    """Convert a FieldShape to a Spark type expression string."""
    match shape:
        case ArrayOf(element=element):
            return f"ArrayType({_shape_to_spark(element)}, True)"
        case NewTypeShape(inner=inner):
            return _shape_to_spark(inner)
        case ModelRef(model=m):
            return _struct_type_expr(m.fields)
        case UnionRef(union=u):
            return _struct_type_expr(_deduplicate_by_name(u.fields))
        case MapOf(key=k, value=v):
            return f"MapType({_shape_to_spark(k)}, {_shape_to_spark(v)}, True)"
        case Primitive() | LiteralScalar() | AnyScalar() as s:
            return _spark_for_scalar(s)
    raise TypeError(f"Unhandled FieldShape: {shape!r}")


def build_schema(spec: FeatureSpec) -> list[SchemaField]:
    """Build schema fields for a feature spec.

    Walks the field tree and maps types to Spark type expressions.
    Recognizes shared types and emits fields in model order.

    Parameters
    ----------
    spec
        The feature spec to build schema fields for.

    Returns
    -------
    list[SchemaField]
        One entry per schema column in model order.
    """
    source_fields = (
        _deduplicate_by_name(spec.fields)
        if isinstance(spec, UnionSpec)
        else spec.fields
    )
    return [
        SchemaField(name=f.name, type_expr=_shape_to_spark(f.shape))
        for f in source_fields
    ]
