"""Markdown generation pipeline: render pages without I/O.

Orchestrates tree expansion, type collection, placement, reverse
references, and rendering into a list of RenderedPage objects. The
caller decides what to do with them (write to disk, add frontmatter,
stream to stdout, etc.).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

import overture.schema.system.primitive as _system_primitive
from overture.schema.system.primitive import GeometryType

from .example_loader import ExampleRecord, load_examples
from .link_computation import LinkContext
from .markdown_renderer import (
    render_enum,
    render_feature,
    render_geometry_from_values,
    render_newtype,
    render_primitives_from_specs,
)
from .model_extraction import expand_model_tree
from .path_assignment import (
    GEOMETRY_PAGE,
    PRIMITIVES_PAGE,
    build_placement_registry,
    resolve_output_path,
)
from .primitive_extraction import (
    extract_primitives,
    partition_primitive_and_geometry_names,
)
from .reverse_references import UsedByEntry, compute_reverse_references
from .specs import (
    EnumSpec,
    FeatureSpec,
    ModelSpec,
    NewTypeSpec,
    SupplementarySpec,
    TypeIdentity,
    UnionSpec,
)
from .type_collection import collect_all_supplementary_types

__all__ = ["RenderedPage", "generate_markdown_pages"]


@dataclass(frozen=True, slots=True)
class RenderedPage:
    """A rendered page with its content and output path."""

    content: str
    path: PurePosixPath
    is_feature: bool = False


def _load_model_examples(
    spec: FeatureSpec,
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
    """Render a single supplementary page (enum, NewType, or sub-model)."""
    output_path = resolve_output_path(tid, registry)
    ctx = LinkContext(output_path, registry)
    used_by = reverse_refs.get(tid)

    if isinstance(spec, EnumSpec):
        content = render_enum(spec, link_ctx=ctx, used_by=used_by)
    elif isinstance(spec, NewTypeSpec):
        content = render_newtype(spec, ctx, used_by=used_by)
    elif isinstance(spec, ModelSpec):
        content = render_feature(spec, ctx, used_by=used_by)
    else:
        raise TypeError(f"Unhandled SupplementarySpec variant: {type(spec).__name__}")

    return RenderedPage(content=content, path=output_path)


def generate_markdown_pages(
    feature_specs: Sequence[FeatureSpec],
    schema_root: str,
) -> list[RenderedPage]:
    """Generate all markdown pages from feature specs.

    Returns rendered pages without writing to disk. The caller handles
    I/O, frontmatter injection, and any output-format-specific concerns
    (like Docusaurus category files).
    """
    cache: dict[type, ModelSpec] = {}
    for spec in feature_specs:
        expand_model_tree(spec, cache)

    primitive_names, geometry_names = partition_primitive_and_geometry_names(
        _system_primitive
    )
    all_specs = collect_all_supplementary_types(feature_specs)
    registry = build_placement_registry(
        feature_specs, all_specs, primitive_names, geometry_names, schema_root
    )

    reverse_refs = compute_reverse_references(feature_specs, all_specs)

    pages: list[RenderedPage] = []

    for spec in feature_specs:
        output_path = registry[spec.identity]
        ctx = LinkContext(output_path, registry)
        examples = _load_model_examples(spec)
        used_by = reverse_refs.get(spec.identity)
        content = render_feature(spec, link_ctx=ctx, examples=examples, used_by=used_by)
        pages.append(RenderedPage(content=content, path=output_path, is_feature=True))

    for tid, supp_spec in all_specs.items():
        pages.append(_render_supplement(tid, supp_spec, registry, reverse_refs))

    pages.append(
        RenderedPage(
            content=render_primitives_from_specs(extract_primitives(primitive_names)),
            path=PRIMITIVES_PAGE,
        )
    )

    pages.append(
        RenderedPage(
            content=render_geometry_from_values([m.value for m in GeometryType]),
            path=GEOMETRY_PAGE,
        )
    )

    return pages
