"""Render a model spec to the STAC Table extension's `table:columns`.

The Column Object is `name` (required), `type`, `description`, plus what v1.3.0
permits from STAC common metadata (`data_type`, `unit`) and from the Vector
extension (`vector:geometry_types`). Everything else the IR carries --
constraints, enum vocabularies, named types, defaults, optionality, nested
field descriptions -- has nowhere to go, so this renderer's real output is the
gap log beside the columns.

Four decisions, none of which anything downstream can check:

1. **The type dialect.** `type` is an unconstrained string, and real catalogs
   carry whatever their generating engine's stringifier produced, in more than
   one dialect and inconsistent case. This renderer emits Arrow, because Arrow
   is what Overture distributes: the release is GeoParquet, and these are the
   names an Arrow reader reports opening it. Both the vocabulary and the
   composite grammar come from `pyarrow`'s own stringifier, and they match
   published catalogs, which name columns `int64`, `string`, `double`,
   `binary` and `struct<...>`. Struct member order comes from the released
   files rather than from a model's declaration order, since the type
   describes the physical column.

   `type` and `data_type` therefore disagree on floats. `data_type` (decision
   3) is bound to STAC common metadata's fixed vocabulary, which names them
   `float32`/`float64`; `type` is bound to Arrow, which names the same two
   `float`/`double`. Harmonising them would make one field lie about the
   vocabulary it claims to speak.

2. **Which walk supplies the union.** Walking only concrete arms misses fields
   that stay un-narrowed in the merged list; walking only the merged list drops
   every non-first arm's contribution at a duplicated name. Neither loss can
   raise, because the arms stringify identically. This renderer walks both,
   emits the merged list -- what a columnar sink stores -- and logs a
   `flatten-collision` for every name where the two disagree.

3. **`data_type` is Overture's own base-type name, not a translation.** STAC
   common metadata's data-type vocabulary (int8/16/32/64, uint8/16/32/64,
   float32/64, `other`) already matches Overture's numeric base-type names, so
   this is an allowlist against that vocabulary rather than a lookup table.
   Every column gets one -- `other` is a member of the vocabulary, not an
   omission -- so most columns resolve to it and only the numerics carry
   signal.

4. **`vector:geometry_types` reads the schema's `GeometryTypeConstraint`, not
   data.** The Vector extension defines the field as the geometry types present
   in the dataset, which by the `table:row_count` precedent this renderer would
   refuse. `GeometryTypeConstraint` is validated on every row, so it bounds
   what a column can contain rather than reporting what it does. A column with
   no such constraint gets neither the field nor a claim about it, and is
   logged as a gap.

   `unit` is not emitted, because Overture Schema has no consistent way to
   encode one. Where a unit varies per row it is a field (`Speed` carries a
   `SpeedUnit`); where it is fixed it appears only in the description prose.
   Neither is a column-level fact, and this renderer does not parse prose.
"""

from __future__ import annotations

import builtins
import datetime as _dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from overture.schema.system.geometric import GeometryTypeConstraint

from ..extraction.enum_extraction import extract_enum
from ..extraction.field import (
    AnyScalar,
    ArrayOf,
    FieldShape,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    UnionRef,
)
from ..extraction.field_walk import enum_source
from ..extraction.specs import NO_DEFAULT, FieldSpec, ModelSpec, UnionSpec
from .exceptions import Kind, TableColumnsGap, TableColumnsUnrepresentable

__all__ = [
    "TABLE_EXTENSION_URI",
    "VECTOR_EXTENSION_URI",
    "TableColumnsDocument",
    "render_table_columns",
]

TABLE_EXTENSION_URI = "https://stac-extensions.github.io/table/v1.3.0/schema.json"

# Recommended (not required) by the Table extension's README for the column
# `vector:geometry_types` is emitted on -- see decision 4 in the module
# docstring. Declared here, not just used, because a field from this
# extension in `table:columns` without the extension in `stac_extensions`
# would not validate; `pipeline.py` adds it to that list exactly when this
# renderer emits the field.
VECTOR_EXTENSION_URI = "https://stac-extensions.github.io/vector/v0.1.0/schema.json"

# Arrow type names, exactly as `pyarrow`'s own stringifier emits them
# (`str(pa.float64())` is `"double"`, not `"float64"`). See decision 1 in the
# module docstring. The sized integers look like a no-op mapping because they
# are one: Overture's base-type names already ARE Arrow's for every sized
# integer, exactly as they already are STAC's in `_STAC_DATA_TYPES` below.
# Only the floats, strings, bytes and time types need translating.
_ARROW_TYPES: dict[str, str] = {
    "int8": "int8",
    "int16": "int16",
    "int32": "int32",
    "int64": "int64",
    "uint8": "uint8",
    "uint16": "uint16",
    "uint32": "uint32",
    "uint64": "uint64",
    "float32": "float",
    "float64": "double",
    "str": "string",
    "bool": "bool",
    "bytes": "binary",
    "datetime": "timestamp[us, tz=UTC]",
    "date": "date32[day]",
}

# The type string a shape with no Arrow type of its own collapses to.
_STRING_TYPE = "string"

# Arrow has no geometry type. GeoParquet stores geometry as WKB in a plain
# binary column and carries the semantics in file-level metadata, so `binary`
# is what an Arrow reader reports for a geometry column. The erasure is logged
# rather than absorbed; see `_scalar_type`.
_GEOMETRY_TYPE = "binary"

# STAC common metadata's `data_type` vocabulary. See decision 3 in the module
# docstring: Overture's own base-type names already ARE this vocabulary for
# every numeric primitive, so this is an allowlist, not a translation table.
_STAC_DATA_TYPES: dict[str, str] = {
    "int8": "int8",
    "int16": "int16",
    "int32": "int32",
    "int64": "int64",
    "uint8": "uint8",
    "uint16": "uint16",
    "uint32": "uint32",
    "uint64": "uint64",
    "float32": "float32",
    "float64": "float64",
}
_OTHER_DATA_TYPE = "other"

# BBox is a plain class the codegen cannot walk, so the physical layout keeps a
# shared struct constant for it. Member order is the `BBox` class's own
# declaration order.
#
# THAT DOES NOT MATCH THE ORDER OVERTURE SHIPS, which is `xmin, xmax, ymin,
# ymax` -- what this repo's PySpark `BBOX_STRUCT` declares and what a reader
# reports for a released file. The discrepancy is accepted rather than encoded:
# this renderer derives types from models, and a constant matching one
# publisher's file layout would be a fact about that publisher rather than
# about the schema. A consumer reading member order off this field will be
# wrong about it.
_BBOX_TYPE = "struct<xmin: double, ymin: double, xmax: double, ymax: double>"

# Pydantic types with no Arrow type of their own. Keyed by NAME rather than by
# `issubclass`: in Pydantic v2 neither `HttpUrl` nor `EmailStr` is a `str`
# subclass, so the builtin fallback below never reaches them.
_PYDANTIC_AS_STRING: frozenset[str] = frozenset(
    {"HttpUrl", "AnyUrl", "AnyHttpUrl", "EmailStr", "UUID"}
)

# Fallback keyed on the underlying Python type, for constrained-string NewTypes
# the registry has no name entry for. `bool` precedes `int` because it is a
# subclass. A bare Python `int` widens to `int64`, Arrow's own default for one.
_BUILTIN_TYPES: tuple[tuple[type, str], ...] = (
    (bool, "bool"),
    (_dt.datetime, "timestamp[us, tz=UTC]"),
    (_dt.date, "date32[day]"),
    (str, _STRING_TYPE),
    (bytes, "binary"),
    (int, "int64"),
    (float, "double"),
)


@dataclass
class Column:
    """One emitted Column Object, plus what the emitter knows and cannot say."""

    name: str
    type: str
    description: str | None
    # Retained for the gap log; never emitted into `table:columns`, which
    # has no field for any of it.
    base_type: str | None
    # The underlying Python type, kept so a downstream target can resolve
    # through the same fallback chain the Arrow type does.
    python_type: builtins.type | None
    enum_name: str | None
    is_literal: bool
    enum_members: tuple[tuple[str, str | None], ...]
    has_default: bool
    is_required: bool
    constraint_names: tuple[str, ...]
    # STAC common metadata's data-type vocabulary name for `base_type`. Always
    # set -- `other` is a member of the vocabulary, not an omission.
    data_type: str
    # GeoJSON geometry type names from `GeometryTypeConstraint`, for a
    # geometry column that carries one. `None` for every other column, and
    # for a geometry column with no such constraint (see decision 4).
    geometry_types: tuple[str, ...] | None = None

    def as_column_object(self) -> dict[str, Any]:
        """Return the Column Object: name, type, description when present,
        `data_type` always, and `vector:geometry_types` when known.

        An absent description is an absent KEY, not an empty string. A silent
        empty string would make an undescribed column indistinguishable from a
        described one in every downstream count.
        """
        obj: dict[str, Any] = {"name": self.name, "type": self.type}
        if self.description is not None:
            obj["description"] = self.description
        obj["data_type"] = self.data_type
        if self.geometry_types is not None:
            obj["vector:geometry_types"] = list(self.geometry_types)
        return obj


@dataclass
class TableColumnsDocument:
    """The emitted STAC fields and the gap log."""

    model: str
    columns: list[Column]
    primary_geometry: str | None
    gaps: tuple[TableColumnsGap, ...]

    def stac_fields(self) -> dict[str, Any]:
        """Return the `table:` fields for a STAC object.

        `table:row_count` is absent: a row count is a property of data, and
        this path has only a schema. Its omission is logged as a gap, so that
        it is distinguishable from having been forgotten.
        """
        fields: dict[str, Any] = {
            "table:columns": [c.as_column_object() for c in self.columns]
        }
        if self.primary_geometry is not None:
            fields["table:primary_geometry"] = self.primary_geometry
        return fields

    @property
    def uses_vector_extension(self) -> bool:
        """Whether any column carries `vector:geometry_types`.

        The pipeline needs this to decide whether `stac_extensions` must also
        declare the Vector extension -- a field from that extension without
        its URI declared would not validate.
        """
        return any(c.geometry_types is not None for c in self.columns)


@dataclass
class _Ctx:
    """Render state: the model name, the gap log, and the recursion guard."""

    model: str
    gaps: list[TableColumnsGap] = field(default_factory=list)
    stack: list[str] = field(default_factory=list)
    # Named-type sites seen anywhere under this model, for the gap log.
    named_sites: list[str] = field(default_factory=list)

    def gap(self, path: str, kind: Kind, capability: str, detail: str) -> None:
        self.gaps.append(
            TableColumnsGap(self.model, path or "/", kind, capability, detail)
        )


def _dedupe(fields: list[FieldSpec], ctx: _Ctx, path: str) -> list[FieldSpec]:
    """Keep one FieldSpec per name, logging every name where arms disagree.

    The physical layout keeps the first and says nothing. Keeping the first is
    right -- one column stores one type -- but the silence is not: the dropped
    arm's enum vocabulary and description are gone with no trace in the output.
    """
    seen: dict[str, FieldSpec] = {}
    for f in fields:
        prior = seen.get(f.name)
        if prior is None:
            seen[f.name] = f
            continue
        kept, dropped = _vocabulary_of(prior.shape), _vocabulary_of(f.shape)
        ctx.gap(
            f"{path}/{f.name}",
            "flatten-collision",
            "union arm merge",
            f"two union arms contribute a column named {f.name!r}; the first is "
            f"kept ({kept or 'no vocabulary'}) and the other's meaning "
            f"({dropped or 'no vocabulary'}) is discarded. Both stringify to the "
            "same physical type, so the layout's compatibility check cannot "
            "refuse it and nothing downstream records the loss.",
        )
    return list(seen.values())


def _vocabulary_of(shape: FieldShape) -> str | None:
    """Name the enum backing a shape, for collision reporting."""
    inner = _unwrap(shape)
    if isinstance(inner, Primitive):
        src = enum_source(inner)
        if src is not None:
            return src.__name__
        return inner.base_type
    return type(inner).__name__


def _unwrap(shape: FieldShape) -> FieldShape:
    """Strip NewType wrappers, returning the structural shape beneath."""
    while isinstance(shape, NewTypeShape):
        shape = shape.inner
    return shape


def _data_type(base_type: str | None) -> str:
    """Map a column's base type to the STAC common-metadata `data_type` vocabulary.

    Total, unlike `type`: `other` is itself a vocabulary member, so every
    column gets a value. `base_type` is `None` for anything that is not a
    terminal `Primitive` (a struct, array, map, enum, or union column), which
    resolves to `other` exactly like a primitive with no numeric identity.
    """
    if base_type is None:
        return _OTHER_DATA_TYPE
    return _STAC_DATA_TYPES.get(base_type, _OTHER_DATA_TYPE)


def _geometry_types_of(shape: FieldShape) -> tuple[str, ...] | None:
    """Return the GeoJSON geometry type names a geometry column is constrained to.

    Reads `GeometryTypeConstraint.allowed_types` -- see decision 4 in the
    module docstring for why this schema constraint is a legitimate source for
    `vector:geometry_types`. Returns `None` when the shape isn't a geometry
    column, or is one with no such constraint attached.
    """
    inner = _unwrap(shape)
    if not isinstance(inner, Primitive):
        return None
    for source in inner.constraints:
        if isinstance(source.constraint, GeometryTypeConstraint):
            return tuple(
                sorted(t.geo_json_type for t in source.constraint.allowed_types)
            )
    return None


def _top_fields(spec: ModelSpec, ctx: _Ctx) -> list[FieldSpec]:
    """Top-level columns, the way a columnar sink sees them."""
    if isinstance(spec, UnionSpec):
        merged = _dedupe(spec.fields, ctx, "")
        _report_arm_only_types(spec, merged, ctx)
        return merged
    return spec.fields


def _report_arm_only_types(
    union: UnionSpec, merged: list[FieldSpec], ctx: _Ctx
) -> None:
    """Log named types reachable from the arms but not from the merged list.

    The mirror of `_dedupe`'s loss, and the one the doc pipeline and both prior
    renderers see while this walk does not. Reported rather than merged in: the
    merged list is what the column layout is, so adding arm-only types to it
    would misdescribe the emitted table.
    """
    merged_names: set[str] = set()
    for f in merged:
        _collect_type_names(f.shape, merged_names)
    arm_names: set[str] = set()
    for member in union.member_specs:
        for f in member.spec.fields:
            _collect_type_names(f.shape, arm_names)
    only_arm = sorted(arm_names - merged_names)
    if only_arm:
        ctx.gap(
            "",
            "flatten-collision",
            "arm-only named types",
            f"reachable from the union's concrete arms but not from the merged "
            f"field list this table is built from: {', '.join(only_arm)}. A walk "
            "over either side alone under-counts, in opposite directions.",
        )


def _collect_type_names(shape: FieldShape, acc: set[str], depth: int = 0) -> None:
    """Every named type reachable from *shape*: NewTypes, records, unions, enums."""
    if depth > 40:
        return
    match shape:
        case NewTypeShape(name=name, inner=inner):
            if name:
                acc.add(name)
            _collect_type_names(inner, acc, depth + 1)
        case ArrayOf(element=element):
            _collect_type_names(element, acc, depth + 1)
        case MapOf(key=key, value=value):
            _collect_type_names(key, acc, depth + 1)
            _collect_type_names(value, acc, depth + 1)
        case ModelRef(model=model, starts_cycle=starts_cycle):
            acc.add(model.name)
            if not starts_cycle:
                for f in model.fields:
                    _collect_type_names(f.shape, acc, depth + 1)
        case UnionRef(union=union):
            acc.add(union.name)
            for f in union.fields:
                _collect_type_names(f.shape, acc, depth + 1)
        case Primitive() as prim:
            src = enum_source(prim)
            if src is not None:
                acc.add(src.__name__)


def _scalar_type(
    scalar: Primitive | LiteralScalar | AnyScalar, ctx: _Ctx, path: str
) -> str:
    """Map a terminal shape to an Arrow type string, logging what that costs."""
    if isinstance(scalar, LiteralScalar):
        ctx.gap(
            path,
            "target-gap",
            "literal alternatives",
            f"Literal{list(scalar.values)!r} narrows the column to "
            f"{len(scalar.values)} value(s); a Column Object has no enum, const "
            "or pattern keyword, so the column is a bare string.",
        )
        return _STRING_TYPE
    if isinstance(scalar, AnyScalar):
        ctx.gap(
            path,
            "target-gap",
            "any",
            "typing.Any has no column type. Emitted as string to match what the "
            "physical layout stores, which is a stringification, not a type.",
        )
        return _STRING_TYPE
    src = enum_source(scalar)
    if src is not None:
        spec = extract_enum(src)
        described = sum(1 for m in spec.members if m.description is not None)
        ctx.gap(
            path,
            "target-gap",
            "enum vocabulary",
            f"{src.__name__}: {len(spec.members)} members ({described} described) "
            "collapse to a bare string; table:columns has no enum keyword.",
        )
        return _STRING_TYPE
    if scalar.base_type == "BBox":
        return _BBOX_TYPE
    if scalar.base_type == "Geometry":
        ctx.gap(
            path,
            "target-dialect",
            "semantic type erased",
            "Arrow has no geometry type: GeoParquet stores geometry as WKB in a "
            "binary column and keeps the semantics in file-level metadata, which "
            "a type string cannot reach. vector:geometry_types carries the part "
            "of the semantic the schema can assert; the type string carries none "
            "of it.",
        )
        return _GEOMETRY_TYPE
    mapped = _ARROW_TYPES.get(scalar.base_type)
    if mapped is not None:
        return mapped
    source_type = scalar.source_type
    if scalar.base_type in _PYDANTIC_AS_STRING or (
        source_type is not None and source_type.__name__ in _PYDANTIC_AS_STRING
    ):
        ctx.gap(
            path,
            "target-dialect",
            "semantic type erased",
            f"{scalar.base_type} has no Arrow type of its own and stringifies to "
            "string; the semantics live only in the name, which the column does "
            "not carry.",
        )
        return _STRING_TYPE
    if source_type is not None:
        by_name = _ARROW_TYPES.get(source_type.__name__)
        if by_name is not None:
            return by_name
        for py_type, name in _BUILTIN_TYPES:
            if isinstance(source_type, type) and issubclass(source_type, py_type):
                ctx.gap(
                    path,
                    "target-dialect",
                    "semantic type erased",
                    f"{source_type.__name__} has no Arrow type of its own and "
                    f"stringifies to {name}; the semantics live only in the name, "
                    "which the column does not carry.",
                )
                return name
    ctx.gap(
        path,
        "renderer-gap",
        "unmapped base type",
        f"no Arrow type for base_type={scalar.base_type!r} "
        f"(source_type={getattr(source_type, '__name__', None)!r}).",
    )
    return _STRING_TYPE


def _type_string(shape: FieldShape, ctx: _Ctx, path: str) -> str:
    """Build the Arrow type string for a column, recursing into nesting.

    Nesting lives in the type string, not in the column name: published
    catalogs do not put dots in column names.

    Composites use Arrow's angle-bracket grammar -- `struct<name: type, ...>`,
    `list<item: type>`, `map<key, value>` -- taken from `pyarrow`'s
    stringifier. A list's child is named `item`, pyarrow's constructor form. A
    round-trip through a Parquet file renames it `element`, since the Parquet
    LIST logical type fixes that name, and the same round-trip stringifies a
    map as `map<string, string ('mp')>`, appending the Parquet group name.
    Those are artifacts of the file rather than type names.
    """
    match shape:
        case NewTypeShape(name=name, inner=inner):
            if name:
                ctx.named_sites.append(f"{path}:{name}")
            return _type_string(inner, ctx, path)
        case ArrayOf(element=element):
            return f"list<item: {_type_string(element, ctx, path + '[]')}>"
        case MapOf(key=key, value=value):
            key_type = _type_string(key, ctx, path + "/key")
            value_type = _type_string(value, ctx, path + "/value")
            return f"map<{key_type}, {value_type}>"
        case ModelRef(model=model, starts_cycle=starts_cycle):
            ctx.named_sites.append(f"{path}:{model.name}")
            if starts_cycle or model.name in ctx.stack:
                raise TableColumnsUnrepresentable(
                    (
                        TableColumnsGap(
                            ctx.model,
                            path,
                            "target-gap",
                            "recursion",
                            f"{model.name} is recursive; a type string has no "
                            "way to name a type, so a cycle cannot terminate.",
                        ),
                    )
                )
            ctx.stack.append(model.name)
            try:
                return _struct_string(model.fields, ctx, path, model.name)
            finally:
                ctx.stack.pop()
        case UnionRef(union=union):
            ctx.named_sites.append(f"{path}:{union.name}")
            if union.name in ctx.stack:
                raise TableColumnsUnrepresentable(
                    (
                        TableColumnsGap(
                            ctx.model,
                            path,
                            "target-gap",
                            "recursion",
                            f"{union.name} is recursive; see above.",
                        ),
                    )
                )
            ctx.stack.append(union.name)
            try:
                merged = _dedupe(union.fields, ctx, path)
                _report_arm_only_types(union, merged, ctx)
                ctx.gap(
                    path,
                    "target-gap",
                    "discriminated union",
                    f"{union.name} has {len(union.members)} arms; the column is a "
                    "single struct of their merged fields, and the discriminator "
                    "survives only as a string. Which arm a row belongs to is not "
                    "recoverable from the schema.",
                )
                return _struct_string(merged, ctx, path, union.name)
            finally:
                ctx.stack.pop()
        case Primitive() | LiteralScalar() | AnyScalar() as scalar:
            return _scalar_type(scalar, ctx, path)
    raise TypeError(f"Unhandled FieldShape: {shape!r}")


def _struct_string(fields: list[FieldSpec], ctx: _Ctx, path: str, owner: str) -> str:
    """`struct<name: type, ...>`, logging the descriptions that die inside it."""
    if not fields:
        ctx.gap(
            path,
            "renderer-gap",
            "empty struct",
            f"{owner} has no fields; an empty struct column cannot carry data.",
        )
        return "struct<>"
    parts = []
    for f in fields:
        member_path = f"{path}/{f.name}"
        if f.description is not None:
            ctx.gap(
                member_path,
                "target-gap",
                "nested description",
                f"{owner}.{f.name} is described, and a Column Object describes "
                "only top-level columns. The NAME survives inside the type "
                "string; the description does not.",
            )
        _log_field_surplus(f, ctx, member_path, nested=True)
        parts.append(f"{f.name}: {_type_string(f.shape, ctx, member_path)}")
    return f"struct<{', '.join(parts)}>"


def _constraint_names(shape: FieldShape, acc: list[str], depth: int = 0) -> None:
    """Collect constraint class names at every layer of a shape."""
    if depth > 40:
        return
    for source in getattr(shape, "constraints", ()) or ():
        acc.append(type(source.constraint).__name__)
    match shape:
        case NewTypeShape(inner=inner):
            _constraint_names(inner, acc, depth + 1)
        case ArrayOf(element=element):
            _constraint_names(element, acc, depth + 1)
        case MapOf(key=key, value=value):
            _constraint_names(key, acc, depth + 1)
            _constraint_names(value, acc, depth + 1)
        case ModelRef(model=model, starts_cycle=starts_cycle):
            if not starts_cycle:
                for f in model.fields:
                    _constraint_names(f.shape, acc, depth + 1)
        case UnionRef(union=union):
            for f in union.fields:
                _constraint_names(f.shape, acc, depth + 1)


def _log_field_surplus(f: FieldSpec, ctx: _Ctx, path: str, *, nested: bool) -> None:
    """Log the per-field capabilities a Column Object has no field for."""
    where = "nested field" if nested else "column"
    if f.default is not NO_DEFAULT:
        ctx.gap(
            path,
            "target-gap",
            "default",
            f"{where} carries default={f.default!r}. The IR carries defaults; a "
            "Column Object is name/type/description and has nowhere to put one. "
            "The gap is the target's, not the IR's.",
        )
    if f.is_deprecated:
        ctx.gap(
            path,
            "target-gap",
            "deprecated",
            f"{where} is deprecated; there is no keyword for it.",
        )
    ctx.gap(
        path,
        "target-gap",
        "optionality",
        f"{where} is {'required' if f.is_required else 'optional'}"
        f"{' and nullable' if f.is_optional else ''}; a Column Object has no "
        "required, nullable or optional keyword, so this is not expressible at "
        "all.",
    )
    names: list[str] = []
    _constraint_names(f.shape, names)
    for name in names:
        ctx.gap(
            path,
            "target-gap",
            "constraint",
            f"{name} has no representation: the Column Object vocabulary is "
            "name, type, description.",
        )


def _enum_of(shape: FieldShape) -> type[Enum] | None:
    inner = _unwrap(shape)
    return enum_source(inner) if isinstance(inner, Primitive) else None


def render_table_columns(
    spec: ModelSpec, *, strict: bool = False
) -> TableColumnsDocument:
    """Render *spec* to STAC `table:` fields, with a gap log beside them.

    `strict=True` raises rather than returning a non-empty log. A `UnionSpec`
    root emits normally: a flat column list is exactly
    what a columnar sink stores for a union, and the IR already carries the
    merged field list that sink needs.
    """
    ctx = _Ctx(model=spec.name)
    columns: list[Column] = []
    for f in _top_fields(spec, ctx):
        path = f"/{f.name}"
        _log_field_surplus(f, ctx, path, nested=False)
        inner = _unwrap(f.shape)
        enum_cls = _enum_of(f.shape)
        members: tuple[tuple[str, str | None], ...] = ()
        if enum_cls is not None:
            members = tuple(
                (m.value, m.description) for m in extract_enum(enum_cls).members
            )
        constraints: list[str] = []
        _constraint_names(f.shape, constraints)
        base_type = inner.base_type if isinstance(inner, Primitive) else None
        geometry_types = _geometry_types_of(f.shape)
        if base_type == "Geometry" and geometry_types is None:
            ctx.gap(
                path,
                "ir-gap",
                "geometry types",
                "geometry column has no GeometryTypeConstraint; "
                "vector:geometry_types would have to guess which types can "
                "appear, so it is omitted rather than claiming all seven.",
            )
        columns.append(
            Column(
                name=f.name,
                type=_type_string(f.shape, ctx, path),
                description=f.description,
                base_type=base_type,
                python_type=(
                    inner.source_type
                    if isinstance(inner, Primitive)
                    and isinstance(inner.source_type, type)
                    else None
                ),
                enum_name=enum_cls.__name__ if enum_cls is not None else None,
                is_literal=isinstance(inner, LiteralScalar),
                enum_members=members,
                has_default=f.default is not NO_DEFAULT,
                is_required=f.is_required,
                constraint_names=tuple(constraints),
                data_type=_data_type(base_type),
                geometry_types=geometry_types,
            )
        )

    primary = _primary_geometry(columns, ctx)
    gaps = tuple(ctx.gaps)
    if strict and gaps:
        raise TableColumnsUnrepresentable(gaps)
    return TableColumnsDocument(
        model=spec.name,
        columns=columns,
        primary_geometry=primary,
        gaps=gaps,
    )


def _primary_geometry(columns: list[Column], ctx: _Ctx) -> str | None:
    """Derive `table:primary_geometry`, refusing to guess when it is ambiguous."""
    geometry = [c.name for c in columns if c.base_type == "Geometry"]
    if len(geometry) == 1:
        return geometry[0]
    if not geometry:
        ctx.gap(
            "",
            "target-gap",
            "primary geometry",
            "no geometry column; table:primary_geometry is omitted.",
        )
        return None
    ctx.gap(
        "",
        "ir-gap",
        "primary geometry",
        f"{len(geometry)} geometry columns ({', '.join(geometry)}) and nothing in "
        "the IR says which is primary. Omitted rather than guessed -- picking the "
        "first would invent a fact about the data.",
    )
    return None
