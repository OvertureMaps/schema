"""Build StructType schema source from ModelSpec field trees."""

from __future__ import annotations

from dataclasses import dataclass

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
from ..extraction.field_walk import enum_source
from ..extraction.specs import FieldSpec, ModelSpec, UnionSpec
from ..extraction.type_registry import get_type_mapping

__all__ = [
    "SHARED_TYPE_REFS",
    "SchemaField",
    "build_schema",
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
    if enum_source(scalar) is not None:
        return _STRING_FALLBACK
    return _spark_for_base(scalar.base_type, scalar.source_type)


def _deduplicate_by_name(fields: list[FieldSpec]) -> list[FieldSpec]:
    """Keep one FieldSpec per name, requiring every arm to agree on Spark type.

    Union annotated_fields may contain the same field name declared by
    multiple arms with different `FieldSpec`s -- a `Literal` discriminator
    whose value differs per arm, or a field whose per-arm constraints
    diverge (see `union_extraction.extract_union`). A columnar sink stores
    one type per column name, so the schema needs exactly one entry. Two
    same-named fields are compatible when they resolve to the SAME Spark
    type -- the first-seen `FieldSpec`'s shape is kept (arbitrarily; the
    column type is identical either way). Two same-named fields that resolve
    to DIFFERENT Spark types cannot share one generated column, so this
    always raises, whether the mismatch is numeric (a narrower int type vs a
    float) or not.

    Widening the two to their common type would often work in practice --
    Spark and Parquet can promote a narrower numeric column to a wider one
    (reading an int where the schema declares a double, say). It is forbidden
    anyway: a widened column makes the union's type an implicit property
    inferred from whichever arms happen to disagree, rather than a decision
    stated in the model. Raising forces that decision to the surface at
    generation instead of leaving it as a silent compatibility trap.
    """
    seen: dict[str, FieldSpec] = {}
    for f in fields:
        existing = seen.get(f.name)
        if existing is None:
            seen[f.name] = f
            continue
        spark_f, spark_existing = (
            _shape_to_spark(f.shape),
            _shape_to_spark(existing.shape),
        )
        if spark_f != spark_existing:
            raise ValueError(
                f"Union field {f.name!r} resolves to incompatible Spark "
                f"types across arms ({spark_existing} vs {spark_f}); a "
                "single Parquet column cannot represent both."
            )
    return list(seen.values())


def _struct_type_expr(fields: list[FieldSpec]) -> str:
    """Build an inline `StructType([...])` expression from a list of fields."""
    if not fields:
        raise ValueError(
            "Cannot build a StructType for a model with no fields; an empty "
            "struct column cannot carry data and signals an upstream "
            "extraction problem."
        )
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


def build_schema(spec: ModelSpec) -> list[SchemaField]:
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
