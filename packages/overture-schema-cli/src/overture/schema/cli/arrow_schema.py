"""
Pydantic to PyArrow schema conversion and comparison for Overture models.

This module provides functions to convert Pydantic models to PyArrow schemas,
enabling generation of empty Parquet files with correct schema definitions,
and to compare Arrow schemas for compatibility checking.
"""

from __future__ import annotations

from enum import Enum
from types import NoneType, UnionType
from typing import TYPE_CHECKING, Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .format_adapters import FieldDiff, SchemaDiff

if TYPE_CHECKING:
    import pyarrow as pa

# Re-export for backwards compatibility
__all__ = ["FieldDiff", "SchemaDiff", "compare_schemas", "pydantic_model_to_arrow_schema"]

def _is_newtype(tp: Any) -> bool:
    """Check if a type is a NewType."""
    return callable(tp) and hasattr(tp, "__supertype__")


def _get_newtype_name(tp: Any) -> str | None:
    """Get the name of a NewType, or None if not a NewType."""
    if _is_newtype(tp):
        return getattr(tp, "__name__", None)
    return None


def _unwrap_annotated(tp: Any) -> tuple[Any, list[Any]]:
    """
    Unwrap Annotated type, returning base type and collected metadata.

    Parameters
    ----------
    tp : Any
        A type annotation, possibly Annotated[T, ...]

    Returns
    -------
    tuple[Any, list[Any]]
        Tuple of (base_type, metadata_list)
    """
    metadata: list[Any] = []
    while get_origin(tp) is Annotated:
        args = get_args(tp)
        tp = args[0]
        metadata.extend(args[1:])
    return tp, metadata


def _unwrap_optional(tp: Any) -> tuple[bool, Any]:
    """
    Check if type is T | None (Optional), return (is_optional, inner_type).

    Parameters
    ----------
    tp : Any
        A type annotation

    Returns
    -------
    tuple[bool, Any]
        Tuple of (is_optional, inner_type_or_original)
    """
    origin = get_origin(tp)
    if origin is Union or origin is UnionType:
        args = get_args(tp)
        non_none = [a for a in args if a is not NoneType and a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return True, non_none[0]
    return False, tp


def _is_pydantic_missing(tp: Any) -> bool:
    """Check if type involves Pydantic's MISSING sentinel (Omitable)."""
    try:
        from pydantic.experimental.missing_sentinel import MISSING

        origin = get_origin(tp)
        if origin is Union or origin is UnionType:
            args = get_args(tp)
            return any(a is type(MISSING) or a is MISSING for a in args)
    except ImportError:
        pass
    return False


def _unwrap_missing(tp: Any) -> tuple[bool, Any]:
    """
    Unwrap Omitable[T] which is Annotated[T | MISSING, Field(default=MISSING)].

    Returns (is_omitable, inner_type).
    """
    # First unwrap Annotated
    inner, _ = _unwrap_annotated(tp)

    # Check for MISSING in union
    if _is_pydantic_missing(inner):
        try:
            from pydantic.experimental.missing_sentinel import MISSING

            origin = get_origin(inner)
            if origin is Union or origin is UnionType:
                args = get_args(inner)
                non_missing = [
                    a for a in args if a is not type(MISSING) and a is not MISSING
                ]
                if len(non_missing) == 1:
                    return True, non_missing[0]
        except ImportError:
            pass
    return False, tp


def pydantic_to_arrow_type(
    tp: Any,
    field_info: FieldInfo | None = None,
) -> "pa.DataType":
    """
    Convert a Python/Pydantic type annotation to a PyArrow data type.

    Parameters
    ----------
    tp : Any
        A Python type annotation (may include Annotated, Union, etc.)
    field_info : FieldInfo | None
        Optional Pydantic field info for additional context

    Returns
    -------
    pa.DataType
        The corresponding PyArrow data type
    """
    import pyarrow as pa

    # Import Overture types for comparison
    from overture.schema.system.primitive import BBox, Geometry

    # Unwrap Annotated to get base type
    tp, _metadata = _unwrap_annotated(tp)

    # Handle Omitable[T] (T | MISSING)
    is_omitable, inner = _unwrap_missing(tp)
    if is_omitable:
        tp = inner

    # Handle Optional[T] (T | None)
    is_optional, inner = _unwrap_optional(tp)
    if is_optional:
        tp = inner
        # Unwrap again in case of Annotated[T, ...] | None
        tp, _ = _unwrap_annotated(tp)

    # Check for NewType primitives (int8, int32, float64, etc.)
    newtype_name = _get_newtype_name(tp)
    if newtype_name and newtype_name in {
        "int8", "int16", "int32", "int64",
        "uint8", "uint16", "uint32",
        "float32", "float64",
    }:
        return getattr(pa, newtype_name)()

    # If it's a NewType but not a known primitive, unwrap it
    if _is_newtype(tp):
        tp = tp.__supertype__
        return pydantic_to_arrow_type(tp, field_info)

    # Geometry -> binary (WKB encoding)
    if tp is Geometry or (isinstance(tp, type) and issubclass(tp, Geometry)):
        return pa.binary()

    # BBox -> struct
    # BBoxes are floats, not doubles -- this is intentional; we don't need sub-meter precision + we save a ton of space in our files
    if tp is BBox or (isinstance(tp, type) and issubclass(tp, BBox)):
        return pa.struct(
            [
                pa.field("xmin", pa.float32()),
                pa.field("ymin", pa.float32()),
                pa.field("xmax", pa.float32()),
                pa.field("ymax", pa.float32()),
            ]
        )

    # String enums -> utf8
    if isinstance(tp, type) and issubclass(tp, Enum):
        if issubclass(tp, str):
            return pa.utf8()
        # Non-string enums: use the value type
        return pa.utf8()  # Default to string representation

    # Basic Python types
    if tp is str:
        return pa.utf8()
    if tp is int:
        return pa.int64()
    if tp is float:
        return pa.float64()
    if tp is bool:
        return pa.bool_()
    if tp is bytes:
        return pa.binary()

    # Handle list[T]
    origin = get_origin(tp)
    if origin is list:
        args = get_args(tp)
        if args:
            element_type = pydantic_to_arrow_type(args[0])
            return pa.list_(element_type)
        return pa.list_(pa.utf8())  # Fallback for untyped list

    # Handle dict[K, V] -> map
    if origin is dict:
        args = get_args(tp)
        if len(args) == 2:
            key_type = pydantic_to_arrow_type(args[0])
            value_type = pydantic_to_arrow_type(args[1])
            return pa.map_(key_type, value_type)
        return pa.map_(pa.utf8(), pa.utf8())  # Fallback

    # Handle Pydantic BaseModel -> struct
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return _model_to_struct_type(tp)

    # Fallback: string
    return pa.utf8()


def _model_to_struct_type(model: type[BaseModel]) -> "pa.DataType":
    """
    Convert a Pydantic model to a PyArrow struct type.

    Parameters
    ----------
    model : type[BaseModel]
        A Pydantic model class

    Returns
    -------
    pa.DataType
        A PyArrow struct type with fields matching the model
    """
    import pyarrow as pa

    fields: list[pa.Field] = []

    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        if annotation is None:
            continue

        # Determine nullability
        nullable = _is_field_nullable(field_info)

        # Get the arrow type
        arrow_type = pydantic_to_arrow_type(annotation, field_info)

        # Get field metadata (description, etc.)
        metadata = _get_field_metadata(field_info)

        # Handle aliased fields (e.g., class_ -> class)
        output_name = field_info.alias if field_info.alias else field_name

        fields.append(pa.field(output_name, arrow_type, nullable=nullable, metadata=metadata))

    return pa.struct(fields)


def _is_field_nullable(field_info: FieldInfo) -> bool:
    """Determine if a Pydantic field should be nullable in Arrow."""
    # Check if field has a default (making it optional)
    if not field_info.is_required():
        return True

    # Check if annotation includes None or MISSING
    annotation = field_info.annotation
    if annotation is None:
        return True

    # Unwrap and check for optional/omitable
    is_omitable, _ = _unwrap_missing(annotation)
    if is_omitable:
        return True

    inner, _ = _unwrap_annotated(annotation)
    is_optional, _ = _unwrap_optional(inner)
    return is_optional


def _get_field_metadata(field_info: FieldInfo) -> dict[bytes, bytes] | None:
    """
    Extract metadata from Pydantic FieldInfo for Arrow field metadata.

    Parameters
    ----------
    field_info : FieldInfo
        Pydantic field info

    Returns
    -------
    dict[bytes, bytes] | None
        Arrow-compatible metadata dict, or None if no metadata
    """
    metadata: dict[str, str] = {}

    if field_info.description:
        metadata["description"] = field_info.description

    if field_info.title:
        metadata["title"] = field_info.title

    if not metadata:
        return None

    # Convert to bytes for Arrow
    return {k.encode(): v.encode() for k, v in metadata.items()}


def _extract_model_from_union(tp: Any) -> type[BaseModel] | None:
    """
    If the type is a Union of BaseModels, extract the first one.

    Returns None if the type is not a Union or doesn't contain BaseModels.
    """
    # Already a model class
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return tp

    # Unwrap Annotated
    inner, _ = _unwrap_annotated(tp)

    origin = get_origin(inner)
    if origin is Union or origin is UnionType:
        args = get_args(inner)
        for arg in args:
            # Unwrap Annotated from union members
            unwrapped, _ = _unwrap_annotated(arg)
            if isinstance(unwrapped, type) and issubclass(unwrapped, BaseModel):
                return unwrapped

    return None


def pydantic_model_to_arrow_schema(
    model: type[BaseModel] | Any,
    include_version_metadata: bool = True,
) -> "pa.Schema":
    """
    Convert a Pydantic model class to a PyArrow schema.

    Parameters
    ----------
    model : type[BaseModel] | Any
        A Pydantic model class, or a Union type containing models
    include_version_metadata : bool
        Whether to include schema version in metadata

    Returns
    -------
    pa.Schema
        A PyArrow schema with fields matching the model

    Raises
    ------
    TypeError
        If the model is a Union type that cannot be converted to a single schema
    """
    import pyarrow as pa

    # Handle Union types (like Segment = RoadSegment | RailSegment | WaterSegment)
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        extracted = _extract_model_from_union(model)
        if extracted is not None:
            model = extracted
        else:
            raise TypeError(
                f"Cannot generate Parquet schema for Union type. "
                f"The type '{model}' is a union of multiple models. "
                f"Please specify a more specific type."
            )

    fields: list[pa.Field] = []

    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        if annotation is None:
            continue

        # Determine nullability
        nullable = _is_field_nullable(field_info)

        # Get the arrow type
        arrow_type = pydantic_to_arrow_type(annotation, field_info)

        # Get field metadata
        metadata = _get_field_metadata(field_info)

        # Handle aliased fields
        output_name = field_info.alias if field_info.alias else field_name

        fields.append(pa.field(output_name, arrow_type, nullable=nullable, metadata=metadata))

    # Build schema metadata
    schema_metadata: dict[bytes, bytes] = {}

    if include_version_metadata:
        try:
            from overture.schema.cli.__about__ import __version__

            schema_metadata[b"overture_schema_version"] = __version__.encode()
        except ImportError:
            pass

        schema_metadata[b"model_name"] = model.__name__.encode()
        if model.__module__:
            schema_metadata[b"model_module"] = model.__module__.encode()

    return pa.schema(fields, metadata=schema_metadata if schema_metadata else None)


# ---------------------------------------------------------------------------
# Schema comparison
# ---------------------------------------------------------------------------


def _describe_type(arrow_type: "pa.DataType") -> str:
    """Return a concise, human-readable description of an Arrow data type."""
    import pyarrow as pa

    if isinstance(arrow_type, pa.StructType):
        return f"struct<{arrow_type.num_fields} fields>"
    if isinstance(arrow_type, pa.ListType):
        return f"list<{_describe_type(arrow_type.value_type)}>"
    if isinstance(arrow_type, pa.MapType):
        return f"map<{_describe_type(arrow_type.key_type)}, {_describe_type(arrow_type.item_type)}>"
    return str(arrow_type)


def _compare_types(
    expected_type: "pa.DataType",
    actual_type: "pa.DataType",
    path: str,
    expected_nullable: bool,
    actual_nullable: bool,
) -> list[FieldDiff]:
    """Recursively compare two Arrow data types, returning all differences."""
    import pyarrow as pa

    diffs: list[FieldDiff] = []

    # Required in expected but nullable in actual is a problem
    if not expected_nullable and actual_nullable:
        diffs.append(FieldDiff(
            path=path,
            kind="nullability",
            expected="non-nullable (required)",
            actual="nullable",
        ))

    # Both structs: compare children recursively
    if isinstance(expected_type, pa.StructType) and isinstance(actual_type, pa.StructType):
        actual_children: dict[str, pa.Field] = {}
        for i in range(actual_type.num_fields):
            f = actual_type.field(i)
            actual_children[f.name] = f

        for i in range(expected_type.num_fields):
            ef = expected_type.field(i)
            child_path = f"{path}.{ef.name}"
            if ef.name not in actual_children:
                diffs.append(FieldDiff(
                    path=child_path,
                    kind="missing",
                    expected=_describe_type(ef.type),
                ))
            else:
                af = actual_children[ef.name]
                diffs.extend(_compare_types(
                    ef.type, af.type, child_path, ef.nullable, af.nullable,
                ))

        # Extra children within structs
        expected_child_names = {
            expected_type.field(i).name for i in range(expected_type.num_fields)
        }
        for name, af in actual_children.items():
            if name not in expected_child_names:
                diffs.append(FieldDiff(
                    path=f"{path}.{name}",
                    kind="extra",
                    actual=_describe_type(af.type),
                ))

        return diffs

    # Both lists: compare element types
    if isinstance(expected_type, pa.ListType) and isinstance(actual_type, pa.ListType):
        diffs.extend(_compare_types(
            expected_type.value_type,
            actual_type.value_type,
            f"{path}.item",
            expected_type.value_field.nullable,
            actual_type.value_field.nullable,
        ))
        return diffs

    # Both maps: compare key and value types
    if isinstance(expected_type, pa.MapType) and isinstance(actual_type, pa.MapType):
        diffs.extend(_compare_types(
            expected_type.key_type,
            actual_type.key_type,
            f"{path}.key",
            expected_type.key_field.nullable,
            actual_type.key_field.nullable,
        ))
        diffs.extend(_compare_types(
            expected_type.item_type,
            actual_type.item_type,
            f"{path}.value",
            expected_type.item_field.nullable,
            actual_type.item_field.nullable,
        ))
        return diffs

    # Primitive / category-mismatch comparison
    if expected_type != actual_type:
        diffs.append(FieldDiff(
            path=path,
            kind="type_mismatch",
            expected=_describe_type(expected_type),
            actual=_describe_type(actual_type),
        ))

    return diffs


def compare_schemas(
    expected: "pa.Schema",
    actual: "pa.Schema",
    *,
    ignore_fields: set[str] | None = None,
) -> SchemaDiff:
    """Compare an expected Arrow schema against an actual (file) schema.

    Parameters
    ----------
    expected : pa.Schema
        The schema generated from the Pydantic model.
    actual : pa.Schema
        The schema read from a Parquet file.
    ignore_fields : set[str] | None
        Top-level field names to skip entirely during comparison.

    Returns
    -------
    SchemaDiff
        Complete diff result.
    """
    ignore = ignore_fields or set()
    missing: list[FieldDiff] = []
    extra: list[FieldDiff] = []
    type_mismatches: list[FieldDiff] = []
    nullability_issues: list[FieldDiff] = []

    actual_fields_by_name = {f.name: f for f in actual}

    for expected_field in expected:
        name = expected_field.name
        if name in ignore:
            continue
        if name not in actual_fields_by_name:
            missing.append(FieldDiff(
                path=name,
                kind="missing",
                expected=_describe_type(expected_field.type),
            ))
            continue

        actual_field = actual_fields_by_name[name]
        for d in _compare_types(
            expected_field.type,
            actual_field.type,
            path=name,
            expected_nullable=expected_field.nullable,
            actual_nullable=actual_field.nullable,
        ):
            if d.kind == "nullability":
                nullability_issues.append(d)
            elif d.kind == "missing":
                missing.append(d)
            elif d.kind == "extra":
                extra.append(d)
            else:
                type_mismatches.append(d)

    expected_field_names = set(expected.names)
    for actual_field in actual:
        if actual_field.name in ignore:
            continue
        if actual_field.name not in expected_field_names:
            extra.append(FieldDiff(
                path=actual_field.name,
                kind="extra",
                actual=_describe_type(actual_field.type),
            ))

    return SchemaDiff(
        missing_fields=missing,
        extra_fields=extra,
        type_mismatches=type_mismatches,
        nullability_issues=nullability_issues,
    )
