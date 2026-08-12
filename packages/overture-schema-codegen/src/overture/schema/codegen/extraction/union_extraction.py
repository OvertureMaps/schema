"""Union extraction and discriminator handling."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from overture.schema.system.typing_util import (
    discriminator_values,
    is_model_union,
    model_types,
    model_variants,
    root_annotated_metadata,
    union_discriminator,
)

from .docstring import clean_docstring
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
) -> tuple[str | None, dict[str, type[BaseModel]] | None]:
    """Extract discriminator field name and value-to-type mapping.

    The members come from the annotation itself (via `model_variants`), so the
    mapping and the arm list cannot disagree. When a discriminator exists,
    the mapping must cover every member with at least one key, and every key
    must select exactly one member; a member may contribute several keys
    (pydantic accepts multi-value literal tags -- each value routes to the
    same member). Anything less used to degrade silently -- a member skipped
    here later produced *unguarded* pyspark checks (`check_builder` gates
    variant fields via this mapping) -- so partial or colliding mappings
    raise instead. Nested discriminated unions (a leaf governed by more than
    one discriminator) are rejected the same way: a flat mapping keyed on
    the outer discriminator cannot represent them.

    Raises
    ------
    NotImplementedError
        If a member sits behind a nested discriminator path.
    TypeError
        If a member has no literal discriminator values, two members share a
        key, or a member appears twice.
    """
    disc_field_name = union_discriminator(annotation)
    if disc_field_name is None:
        return None, None

    mapping: dict[str, type[BaseModel]] = {}
    for variant in model_variants(annotation):
        if len(variant.discriminator_path) > 1:
            raise NotImplementedError(
                f"Nested discriminated union: {variant.model.__qualname__} is "
                f"governed by discriminator path {variant.discriminator_path!r}; "
                f"a flat '{disc_field_name}' mapping cannot represent it"
            )
        member = variant.model
        field_info = _find_field_by_alias(member, disc_field_name)
        keys = (
            discriminator_values(field_info.annotation)
            if field_info is not None and field_info.annotation is not None
            else None
        )
        if not keys:
            raise TypeError(
                f"Union member {member.__qualname__} has no literal "
                f"'{disc_field_name}' values; the discriminator mapping must "
                f"cover every member"
            )
        for key in keys:
            if key in mapping:
                raise TypeError(
                    f"Discriminator value {key!r} maps to both "
                    f"{mapping[key].__qualname__} and {member.__qualname__}"
                )
            mapping[key] = member

    return disc_field_name, mapping


_TypeShape = tuple[object, ...]
_FieldKey = tuple[str, _TypeShape, frozenset[object], bool]


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
    if not is_model_union(annotation):
        raise TypeError(f"{name} is not a union type alias")

    members = list(model_types(annotation))
    description = next(
        (
            clean_docstring(m.description)
            for m in root_annotated_metadata(annotation)
            if isinstance(m, FieldInfo) and m.description is not None
        ),
        None,
    )
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
            # The key includes the constraints fingerprint alongside the
            # structural one: two arms with the same name and shape but
            # different constraints (e.g. VehicleAxleCountSelector's
            # `ge=1, le=100, multiple_of=1` vs the other selectors' `ge=0`)
            # must not collapse into one `AnnotatedField` sharing a single
            # constraint set -- that would silently drop one arm's rules.
            # Keeping them as separate rows, each gated to its own
            # `variant_sources`, reuses the same per-arm `Guard` mechanism
            # that already handles a field present on only some arms
            # (`check_builder._field_checks_for_union`), and the renderer's
            # collision resolver already disambiguates multiple `Check`s
            # landing on the same field label. Provenance joins the key so a
            # native field and an identically-shaped extension field never
            # collapse into one row.
            key = (
                fs.name,
                _structural_fingerprint(fs),
                _constraints_fingerprint(fs),
                fs.is_extension,
            )
            existing = seen.get(key)
            prior_sources = existing.variant_sources or () if existing else ()
            seen[key] = AnnotatedField(
                field_spec=fs,
                variant_sources=(*prior_sources, member_cls),
            )

    annotated_fields.extend(seen.values())

    disc_field, disc_mapping = extract_discriminator(annotation)

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
