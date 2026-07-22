"""Markdown generation pipeline: render pages without I/O.

Orchestrates tree expansion, type collection, placement, reverse
references, and rendering into a list of RenderedPage objects. The
caller decides what to do with them (write to disk, add frontmatter,
stream to stdout, etc.).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

import overture.schema.system.geometric as _system_geometric
import overture.schema.system.numeric as _system_numeric
from overture.schema.system.geometric import GeometryType

from ..extraction.examples import ExampleRecord, load_examples
from ..extraction.numeric_extraction import extract_numerics
from ..extraction.specs import (
    EnumSpec,
    ModelSpec,
    NewTypeSpec,
    PydanticTypeSpec,
    RecordSpec,
    SupplementarySpec,
    TypeIdentity,
    UnionSpec,
)
from ..extraction.type_analyzer import is_newtype
from ..layout.type_collection import collect_all_supplementary_types
from .link_computation import LinkContext
from .path_assignment import (
    GEOMETRIC_PAGE,
    NUMERIC_PAGE,
    build_placement_registry,
    resolve_output_path,
)
from .renderer import (
    render_enum,
    render_geometry_from_values,
    render_model,
    render_newtype,
    render_numeric_from_specs,
    render_pydantic_type,
)
from .reverse_references import UsedByEntry, compute_reverse_references

__all__ = [
    "RenderedPage",
    "generate_markdown_pages",
    "partition_numeric_and_geometry_types",
]


@dataclass(frozen=True, slots=True)
class RenderedPage:
    """A rendered page with its content and output path."""

    content: str
    path: PurePosixPath
    is_model: bool = False


def _load_model_examples(
    spec: ModelSpec,
) -> list[ExampleRecord] | None:
    """Load examples for a feature spec, returning None when absent."""
    if isinstance(spec, UnionSpec):
        pyproject_source = spec.members[0] if spec.members else None
        validation_type = spec.source_annotation
        model_fields = spec.common_base.model_fields
    else:
        pyproject_source = spec.source_type
        validation_type = spec.source_type
        model_fields = spec.source_type.model_fields if spec.source_type else {}
    if not pyproject_source:
        return None
    field_names = [f.name for f in spec.fields]
    examples = load_examples(
        validation_type,
        spec.name,
        field_names,
        pyproject_source=pyproject_source,
        model_fields=model_fields,
    )
    return examples or None


def _render_supplement(
    tid: TypeIdentity,
    spec: SupplementarySpec,
    registry: dict[TypeIdentity, PurePosixPath],
    reverse_refs: dict[TypeIdentity, list[UsedByEntry]],
) -> RenderedPage:
    """Render a single supplementary type page."""
    output_path = resolve_output_path(tid, registry)
    ctx = LinkContext(output_path, registry)
    used_by = reverse_refs.get(tid)

    match spec:
        case EnumSpec():
            content = render_enum(spec, link_ctx=ctx, used_by=used_by)
        case NewTypeSpec():
            content = render_newtype(spec, ctx, used_by=used_by)
        case RecordSpec():
            content = render_model(spec, ctx, used_by=used_by)
        case PydanticTypeSpec():
            content = render_pydantic_type(spec, link_ctx=ctx, used_by=used_by)
        case _:
            raise TypeError(
                f"Unhandled SupplementarySpec variant: {type(spec).__name__}"
            )

    return RenderedPage(content=content, path=output_path)


def partition_numeric_and_geometry_types(
    numeric_module: object,
    geometric_module: object,
) -> tuple[list[TypeIdentity], list[TypeIdentity]]:
    """Discover numeric and geometry types from their source modules' exports.

    NewType exports of *numeric_module* are numeric types.
    Non-constraint class/enum exports of *geometric_module* are geometry types.
    """
    numerics: list[TypeIdentity] = []
    for name in getattr(numeric_module, "__all__", []):
        obj = getattr(numeric_module, name)
        if is_newtype(obj):
            numerics.append(TypeIdentity(obj, name))

    geometries: list[TypeIdentity] = []
    for name in getattr(geometric_module, "__all__", []):
        obj = getattr(geometric_module, name)
        if isinstance(obj, type) and not name.endswith("Constraint"):
            geometries.append(TypeIdentity(obj, name))

    return numerics, geometries


def generate_markdown_pages(
    model_specs: Sequence[ModelSpec],
    schema_root: str,
    *,
    alias_specs: Mapping[TypeIdentity, SupplementarySpec] | None = None,
) -> list[RenderedPage]:
    """Generate all markdown pages from feature specs.

    Returns rendered pages without writing to disk. The caller handles
    I/O, frontmatter injection, and any output-format-specific concerns
    (like Docusaurus category files).

    `alias_specs` are supplementary types documented on their own but not
    reachable by walking feature field trees -- a `RootModel` entry point,
    which serializes as its bare root value and so appears in no feature as
    a named reference. They join the collected supplementary types and
    render, place, and cross-reference identically.
    """
    numeric_names, geometry_names = partition_numeric_and_geometry_types(
        _system_numeric, _system_geometric
    )
    all_specs = collect_all_supplementary_types(model_specs)
    if alias_specs:
        all_specs = {**all_specs, **alias_specs}
    registry = build_placement_registry(
        model_specs, all_specs, numeric_names, geometry_names, schema_root
    )

    reverse_refs = compute_reverse_references(model_specs, all_specs)

    pages: list[RenderedPage] = []

    for spec in model_specs:
        output_path = registry[spec.identity]
        ctx = LinkContext(output_path, registry)
        examples = _load_model_examples(spec)
        used_by = reverse_refs.get(spec.identity)
        content = render_model(spec, link_ctx=ctx, examples=examples, used_by=used_by)
        pages.append(RenderedPage(content=content, path=output_path, is_model=True))

    for tid, supp_spec in all_specs.items():
        pages.append(_render_supplement(tid, supp_spec, registry, reverse_refs))

    pages.append(
        RenderedPage(
            content=render_numeric_from_specs(extract_numerics(numeric_names)),
            path=NUMERIC_PAGE,
        )
    )

    pages.append(
        RenderedPage(
            content=render_geometry_from_values([m.value for m in GeometryType]),
            path=GEOMETRIC_PAGE,
        )
    )

    return pages
