"""Union extraction and discriminator handling."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Annotated, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from overture.schema.system.feature import resolve_discriminator_field_name

from .field import (
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
from .field_walk import list_depth, terminal_of, walk_shape
from .model_extraction import extract_model, resolve_field_alias
from .specs import AnnotatedField, FieldSpec, MemberSpec, UnionSpec, is_model_class
from .type_analyzer import (
    capture_union_members,
    single_literal_value,
)

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

    return min(common, key=lambda c: (max_mro_index(c), c.__module__, c.__qualname__))


def _find_field_by_alias(model: type[BaseModel], alias: str) -> FieldInfo | None:
    """Find a field in `model_fields` by alias-resolved name."""
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
                key = lit_val.value if isinstance(lit_val, Enum) else str(lit_val)
                mapping[key] = member

    return disc_field_name, mapping or None


_TypeShape = tuple[object, ...]
_FieldKey = tuple[str, _TypeShape]


def _structural_fingerprint(spec: FieldSpec) -> _TypeShape:
    """Structural shape for dedup: ignores per-variant source_type variation.

    Two fields with the same name and same `(terminal_base_type,
    terminal_kind, is_optional, list_depth)` collapse to a single
    `AnnotatedField` whose `variant_sources` lists the contributing
    members.

    `terminal_of` unwraps `ArrayOf` / `NewTypeShape`, so the terminal is
    always one of the six leaf variants below; an unrecognized one
    raises instead of silently collapsing into a shared fingerprint.
    """
    depth = list_depth(spec.shape)
    base_type: object
    terminal = terminal_of(spec.shape)
    match terminal:
        case Primitive(base_type=bt):
            base_type, kind = bt, "scalar"
        case LiteralScalar(values=values):
            base_type, kind = ("Literal", values), "scalar"
        case AnyScalar():
            base_type, kind = "Any", "scalar"
        case ModelRef(model=model):
            base_type, kind = model.name, "model"
        case UnionRef(union=union):
            base_type, kind = union.name, "union"
        case MapOf():
            base_type, kind = "dict", "map"
        case _:
            raise TypeError(f"Unexpected terminal shape: {terminal!r}")
    return (base_type, kind, spec.is_optional, depth)


def _fingerprint_key(constraint: object) -> object:
    """Return a value-stable set key for a single constraint.

    Constraints with value equality -- every `FieldConstraint`, the
    `annotated_types` dataclasses, `GeometryTypeConstraint` -- key as
    themselves. Foreign metadata that falls back to identity equality, namely
    pydantic's internal `Field(...)` metadata, keys on its value-stable `repr`
    so two equal-valued instances still collapse.
    """
    if type(constraint).__eq__ is object.__eq__:
        return repr(constraint)
    return constraint


def _constraints_fingerprint(spec: FieldSpec) -> frozenset[object]:
    """Constraints declared anywhere in *spec*'s shape tree, as a comparable set.

    `_structural_fingerprint` deliberately ignores constraints so that
    members declaring the same field with per-variant `Annotated`
    metadata still collapse to one `AnnotatedField`. This captures what
    that ignores, so collisions with diverging constraints fail loudly
    instead of silently keeping the last member's `FieldSpec`.

    Constraint identity lives on the constraints themselves: `FieldConstraint`
    subclasses define value equality and hashing, so equal rules collapse in
    the set. `_fingerprint_key` covers the lone foreign holdout that still
    compares by identity.
    """
    keys: list[object] = []

    def collect(shape: FieldShape) -> None:
        match shape:
            case (
                Primitive(constraints=cs)
                | LiteralScalar(constraints=cs)
                | AnyScalar(constraints=cs)
                | ArrayOf(constraints=cs)
                | MapOf(constraints=cs)
            ):
                for source in cs:
                    keys.append(_fingerprint_key(source.constraint))
            case ModelRef() | UnionRef() | NewTypeShape():
                pass

    walk_shape(spec.shape, collect)
    return frozenset(keys)


def extract_union(
    name: str,
    annotation: object,
    *,
    entry_point: str | None = None,
    partitions: Mapping[str, str] | None = None,
) -> UnionSpec:
    """Extract a `UnionSpec` from a discriminated union type alias."""
    extracted = capture_union_members(annotation)
    if extracted is None:
        raise TypeError(f"{name} is not a union type alias")
    member_tuple, description = extracted
    members = list(member_tuple)

    common_base = _find_common_base(members)

    # Plain Python type aliases (`Foo = Annotated[...]`) don't preserve
    # the alias name in the annotation. The nested-union path (called
    # from extract_model for UNION-kind fields) passes `members[0].__name__`
    # as the placeholder name. Recover the alias by convention: members
    # extend `<Alias>Base`, so stripping that suffix yields the alias.
    # Top-level unions go through the CLI, which supplies the real name
    # and skips this fallback.
    #
    # PEP 695 (`type Foo = Annotated[...]`) preserves `__name__` as
    # `"Foo"` on 3.12+; after migrating, the placeholder hack can go.
    member_names = {m.__name__ for m in members}
    if name in member_names:
        base_name = common_base.__name__
        name = (
            base_name.removesuffix("Base") if base_name.endswith("Base") else base_name
        )

    base_spec = extract_model(common_base)
    shared_field_names = {f.name for f in base_spec.fields}

    member_specs = [MemberSpec(m, extract_model(m)) for m in members]

    annotated_fields: list[AnnotatedField] = []

    for fs in base_spec.fields:
        annotated_fields.append(AnnotatedField(field_spec=fs, variant_sources=None))

    seen: dict[_FieldKey, AnnotatedField] = {}

    for member in member_specs:
        member_cls = member.member_cls
        for fs in member.spec.fields:
            if fs.name in shared_field_names:
                continue
            key = (fs.name, _structural_fingerprint(fs))
            existing = seen.get(key)
            if existing is not None:
                existing_constraints = _constraints_fingerprint(existing.field_spec)
                if _constraints_fingerprint(fs) != existing_constraints:
                    raise ValueError(
                        f"Union {name!r} field {fs.name!r} has the same structural "
                        f"shape across members but diverging constraints; dedup "
                        f"would silently drop one member's constraints"
                    )
            prior_sources = existing.variant_sources or () if existing else ()
            seen[key] = AnnotatedField(
                field_spec=fs,
                variant_sources=(*prior_sources, member_cls),
            )

    annotated_fields.extend(seen.values())

    disc_field, disc_mapping = extract_discriminator(annotation, members)

    return UnionSpec(
        name=name,
        description=description,
        annotated_fields=annotated_fields,
        members=members,
        member_specs=member_specs,
        discriminator_field=disc_field,
        discriminator_mapping=disc_mapping,
        source_annotation=annotation,
        common_base=common_base,
        entry_point=entry_point,
        partitions=partitions or {},
    )
