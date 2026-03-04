"""Markdown renderer for Pydantic model documentation."""

import functools
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from annotated_types import Interval
from jinja2 import Environment, FileSystemLoader
from typing_extensions import NotRequired

from .example_loader import ExampleRecord
from .field_constraint_description import constraint_display_text
from .link_computation import LinkContext
from .markdown_type_format import (
    format_type,
    format_underlying_type,
    resolve_type_link,
)
from .model_constraint_description import analyze_model_constraints
from .reverse_references import UsedByEntry
from .specs import (
    AnnotatedField,
    EnumSpec,
    FeatureSpec,
    FieldSpec,
    ModelSpec,
    NewTypeSpec,
    PrimitiveSpec,
    PydanticTypeSpec,
    TypeIdentity,
    UnionSpec,
)
from .type_analyzer import (
    ConstraintSource,
)

__all__ = [
    "render_enum",
    "render_feature",
    "render_geometry_from_values",
    "render_newtype",
    "render_primitives_from_specs",
    "render_pydantic_type",
]


_LinkFn = Callable[[TypeIdentity], str]

_TEMPLATES_DIR = Path(__file__).parent / "templates" / "markdown"

_BARE_URL_RE = re.compile(
    r"(?<!\]\()"  # not preceded by ](  (already a Markdown link target)
    r"(https?://[^\s<>)]+|www\.[^\s<>)]+)"
)
_TRAILING_PUNCT_RE = re.compile(r"[.,;:!?]+$")
# (.+?) deliberately does not match newlines -- CommonMark code spans are inline.
_CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")


def _linkify_bare_urls(text: str) -> str:
    """Wrap bare URLs in Markdown link syntax.

    Turns ``www.example.com`` into ``[www.example.com](https://www.example.com)``
    and ``https://example.com`` into ``[https://example.com](https://example.com)``.
    URLs already inside ``[text](url)`` or backtick code spans are left
    untouched. Trailing sentence punctuation (``.``, ``,``, etc.) is excluded
    from the link.

    Two-pass approach: extract code spans first, linkify the remaining
    text, then restore code spans.
    """
    # Extract code spans, replacing with placeholders
    spans: list[str] = []

    def _stash_span(m: re.Match[str]) -> str:
        spans.append(m.group(0))
        return f"\x00CODESPAN{len(spans) - 1}\x00"

    text = _CODE_SPAN_RE.sub(_stash_span, text)

    # Linkify bare URLs in non-code text
    def _to_link(m: re.Match[str]) -> str:
        raw = m.group(0)
        url = _TRAILING_PUNCT_RE.sub("", raw)
        trailing = raw[len(url) :]
        href = url if url.startswith("http") else f"https://{url}"
        return f"[{url}]({href}){trailing}"

    text = _BARE_URL_RE.sub(_to_link, text)

    # Restore code spans
    for i, span in enumerate(spans):
        text = text.replace(f"\x00CODESPAN{i}\x00", span)

    return text


@functools.lru_cache(maxsize=1)
def _get_jinja_env() -> Environment:
    """Return the Jinja2 environment, creating it on first use."""
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["linkify_urls"] = _linkify_bare_urls
    return env


_EXAMPLE_TRUNCATION_LIMIT = 100


class _FieldRow(TypedDict):
    """Template context for a single field table row.

    ``pre_formatted`` indicates the ``name`` already contains backticks
    and variant tags, so the template should render it verbatim.
    """

    name: str
    type_str: str
    description: str | None
    pre_formatted: NotRequired[bool]


_PARAGRAPH_BREAK_RE = re.compile(r"\n(?:[ \t]*\n)+")


def _unwrap_paragraphs(text: str) -> str:
    r"""Unwrap hard-wrapped lines within paragraphs, preserving paragraph breaks.

    Splits on blank lines (paragraph boundaries), replaces single newlines
    within each paragraph with spaces, then rejoins with ``\n\n``.
    Matches markdown's treatment of newlines within paragraphs.
    """
    paragraphs = _PARAGRAPH_BREAK_RE.split(text)
    return "\n\n".join(p.replace("\n", " ") for p in paragraphs)


def _sanitize_for_table_cell(text: str) -> str:
    """Sanitize text for embedding in a markdown table cell.

    Unwraps within-paragraph newlines to spaces, then converts paragraph
    breaks to ``<br/><br/>``. Escapes pipe characters for table safety.
    Uses ``<br/>`` (not ``<br>``) for MDX/Docusaurus compatibility.
    """
    text = text.strip()
    text = _unwrap_paragraphs(text)
    text = text.replace("\n\n", "<br/><br/>")
    return text.replace("|", "\\|")


def _truncate(text: str) -> str:
    """Truncate text to ``_EXAMPLE_TRUNCATION_LIMIT`` chars, adding ellipsis."""
    if len(text) > _EXAMPLE_TRUNCATION_LIMIT:
        return text[: _EXAMPLE_TRUNCATION_LIMIT - 3] + "..."
    return text


def _format_example_value(value: object) -> str:
    """Format an example value for display in a markdown Column | Value table.

    All non-empty values render in backticks for consistent monospace
    formatting. Long representations are truncated before wrapping.
    """
    if value is None:
        return "`null`"

    if isinstance(value, bool):
        return "`true`" if value else "`false`"

    if isinstance(value, str):
        if value == "":
            return ""
        return f"`{_truncate(value)}`"

    if isinstance(value, list):
        items = ", ".join(str(item) for item in value)
        return f"`{_truncate(f'[{items}]')}`"

    if isinstance(value, dict):
        pairs = ", ".join(f"{k}: {v}" for k, v in value.items())
        return f"`{_truncate(f'{{{pairs}}}')}`"

    return f"`{value}`"


def _field_template_context(
    field: FieldSpec,
    ctx: LinkContext | None = None,
) -> _FieldRow:
    """Build template context dict for a field."""
    description = (
        _sanitize_for_table_cell(field.description) if field.description else None
    )
    return _FieldRow(
        name=field.name,
        type_str=format_type(field, ctx),
        description=description,
    )


def _annotate_constraint_notes(
    row: _FieldRow,
    notes: list[str],
) -> None:
    """Append italic constraint descriptions to a field's description cell."""
    formatted = "<br/>".join(f"*{note}*" for note in notes)
    if row["description"]:
        row["description"] = f"{row['description']}<br/><br/>{formatted}"
    else:
        row["description"] = formatted


def _link_fn_from_ctx(ctx: LinkContext | None) -> _LinkFn:
    r"""Build a TypeIdentity-to-markdown-link resolver from a LinkContext.

    Returns a function that resolves a TypeIdentity to ``[`Name`](href)``
    when the identity has a page in the registry, or plain ``\`Name\``` otherwise.
    """
    return functools.partial(resolve_type_link, ctx=ctx)


def _annotate_field_constraints(
    row: _FieldRow, field: FieldSpec, ctx: LinkContext | None
) -> None:
    """Annotate a field row with constraints from the field's own annotation.

    Shows constraints where source is None — those applied directly to
    the field, not inherited from NewType chains. NewType-inherited
    constraints appear on the NewType's own page instead.
    """
    link_fn = _link_fn_from_ctx(ctx)
    notes = [
        constraint_display_text(cs, link_fn=link_fn)
        for cs in field.type_info.constraints
        if cs.source_ref is None
    ]
    if notes:
        _annotate_constraint_notes(row, notes)


def _expandable_list_suffix(field_spec: FieldSpec) -> str:
    """Return ``"[]"`` per nesting level for list-of-model fields expanded inline."""
    if (
        field_spec.type_info.is_list
        and field_spec.model
        and not field_spec.starts_cycle
    ):
        return "[]" * field_spec.type_info.list_depth
    return ""


def _expand_sub_model(
    field_spec: FieldSpec,
    name: str,
    ctx: LinkContext | None,
    result: list[_FieldRow],
) -> None:
    """Expand sub-model fields inline, appending child rows to *result*."""
    sub = field_spec.model if not field_spec.starts_cycle else None
    if sub is not None:
        child_prefix = f"{name}{_expandable_list_suffix(field_spec)}."
        result.extend(_expand_model_fields(sub.fields, ctx, prefix=child_prefix))


def _annotate_top_level_constraints(
    rows: list[_FieldRow],
    constraint_notes: dict[str, list[str]] | None,
) -> None:
    """Annotate top-level field rows with model-constraint notes.

    Top-level rows are those without dot-notation prefixes.
    """
    if not constraint_notes:
        return
    for row in rows:
        name = row["name"]
        if "." in name:
            continue
        field_name = name.split("[")[0]
        if field_name in constraint_notes:
            _annotate_constraint_notes(row, constraint_notes[field_name])


def _expand_model_fields(
    fields: list[FieldSpec],
    ctx: LinkContext | None,
    prefix: str = "",
) -> list[_FieldRow]:
    """Flatten nested model fields into dot-notation rows for display.

    Walks the pre-populated FieldSpec.model tree. Stops recursion at
    fields marked with starts_cycle.
    """
    result: list[_FieldRow] = []
    for field_spec in fields:
        row = _field_template_context(field_spec, ctx)
        name = f"{prefix}{field_spec.name}" if prefix else field_spec.name
        row["name"] = f"{name}{_expandable_list_suffix(field_spec)}"
        if not prefix:
            _annotate_field_constraints(row, field_spec, ctx)
        result.append(row)

        _expand_sub_model(field_spec, name, ctx, result)
    return result


def _short_variant_name(class_name: str, union_name: str) -> str:
    """Strip common suffix to produce short variant name.

    Examples
    --------
    >>> _short_variant_name("RoadSegment", "Segment")
    'Road'
    >>> _short_variant_name("WaterSegment", "Segment")
    'Water'
    >>> _short_variant_name("Building", "Building")
    'Building'
    """
    if class_name.endswith(union_name):
        short = class_name[: -len(union_name)]
        if short:
            return short
    return class_name


def _variant_tag(annotated: AnnotatedField, union_name: str) -> str | None:
    """Return an italic variant tag like ``*(Road, Water)*``, or None for shared fields."""
    if annotated.variant_sources is None:
        return None
    short_names = [
        _short_variant_name(v, union_name) for v in annotated.variant_sources
    ]
    return f" *({', '.join(short_names)})*"


def _expand_union_fields(
    spec: UnionSpec,
    ctx: LinkContext | None,
    constraint_notes: dict[str, list[str]] | None = None,
) -> list[_FieldRow]:
    """Expand UnionSpec fields with inline variant tags.

    Shared fields (variant_sources=None) render normally. Variant-specific
    fields get *(ShortName)* tag after the field name.
    """
    result: list[_FieldRow] = []
    for annotated in spec.annotated_fields:
        field_spec = annotated.field_spec
        row = _field_template_context(field_spec, ctx)
        name = field_spec.name
        suffix = _expandable_list_suffix(field_spec)

        _annotate_field_constraints(row, field_spec, ctx)
        if constraint_notes and field_spec.name in constraint_notes:
            _annotate_constraint_notes(row, constraint_notes[field_spec.name])

        tag = _variant_tag(annotated, spec.name)
        if tag is not None:
            row["name"] = f"`{name}{suffix}`{tag}"
            row["pre_formatted"] = True
        else:
            row["name"] = f"{name}{suffix}"

        result.append(row)
        _expand_sub_model(field_spec, name, ctx, result)
    return result


def render_feature(
    spec: FeatureSpec,
    link_ctx: LinkContext | None = None,
    examples: list[ExampleRecord] | None = None,
    used_by: list[UsedByEntry] | None = None,
) -> str:
    """Render a FeatureSpec (ModelSpec or UnionSpec) as Markdown documentation.

    For ModelSpec, requires expand_model_tree to have been called first.
    For UnionSpec, adds inline variant tags to variant-specific fields.
    """
    template = _get_jinja_env().get_template("feature.md.jinja2")

    constraint_descriptions, field_notes = analyze_model_constraints(spec.constraints)

    if isinstance(spec, UnionSpec):
        fields = _expand_union_fields(spec, link_ctx, constraint_notes=field_notes)
    elif isinstance(spec, ModelSpec):
        fields = _expand_model_fields(spec.fields, link_ctx)
        _annotate_top_level_constraints(fields, field_notes)
    else:
        raise TypeError(f"Unsupported spec type: {type(spec).__name__}")

    formatted_examples: list[list[dict[str, str]]] | None = None
    if examples:
        formatted_examples = [
            [
                {"column": key, "value": _format_example_value(val)}
                for key, val in record.rows
            ]
            for record in examples
        ]

    return template.render(
        model=spec,
        fields=fields,
        constraints=constraint_descriptions,
        examples=formatted_examples,
        used_by=_build_used_by_context(used_by, link_ctx),
    )


def render_enum(
    enum_spec: EnumSpec,
    link_ctx: LinkContext | None = None,
    used_by: list[UsedByEntry] | None = None,
) -> str:
    """Render an EnumSpec as Markdown documentation."""
    template = _get_jinja_env().get_template("enum.md.jinja2")
    return template.render(
        enum=enum_spec, used_by=_build_used_by_context(used_by, link_ctx)
    )


@dataclass
class _NewTypeConstraintRow:
    """Rendered constraint for template."""

    display: str
    source: str | None = None
    source_link: str | None = None


def _format_constraint(
    cs: ConstraintSource,
    newtype_ref: object,
    ctx: LinkContext | None = None,
) -> _NewTypeConstraintRow:
    """Format a ConstraintSource for display in a NewType page."""
    display = constraint_display_text(cs)

    if cs.source_ref is None or cs.source_ref is newtype_ref:
        return _NewTypeConstraintRow(display=display)

    assert cs.source_name is not None  # source_ref and source_name are set together
    source_identity = TypeIdentity(cs.source_ref, cs.source_name)
    source_link = ctx.resolve_link(source_identity) if ctx else None
    return _NewTypeConstraintRow(
        display=display, source=cs.source_name, source_link=source_link
    )


class _UsedByContext(TypedDict):
    """Template context for a used-by entry."""

    name: str
    link: str | None


def _build_used_by_context(
    used_by: list[UsedByEntry] | None,
    link_ctx: LinkContext | None,
) -> list[_UsedByContext] | None:
    """Build template context for used-by entries."""
    if not used_by:
        return None
    return [
        {
            "name": entry.identity.name,
            "link": link_ctx.resolve_link(entry.identity) if link_ctx else None,
        }
        for entry in used_by
    ]


def render_newtype(
    newtype_spec: NewTypeSpec,
    link_ctx: LinkContext | None = None,
    used_by: list[UsedByEntry] | None = None,
) -> str:
    """Render a NewTypeSpec as Markdown documentation."""
    template = _get_jinja_env().get_template("newtype.md.jinja2")
    ti = newtype_spec.type_info
    underlying = format_underlying_type(ti, link_ctx)
    constraints = [
        _format_constraint(cs, newtype_spec.source_type, link_ctx)
        for cs in ti.constraints
    ]

    return template.render(
        newtype=newtype_spec,
        underlying_type=underlying,
        constraints=constraints,
        used_by=_build_used_by_context(used_by, link_ctx),
    )


def render_pydantic_type(
    spec: PydanticTypeSpec,
    link_ctx: LinkContext | None = None,
    used_by: list[UsedByEntry] | None = None,
) -> str:
    """Render a PydanticTypeSpec as Markdown documentation."""
    template = _get_jinja_env().get_template("pydantic_type.md.jinja2")
    return template.render(
        pydantic_type=spec,
        used_by=_build_used_by_context(used_by, link_ctx),
    )


# Matches the ge/le bounds of the int64 NewType in overture.schema.system.primitive.
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1

_NumericBound = int | float | None

# IEEE 754 precision by bit width — formatting knowledge, not schema data.
_FLOAT_PRECISION: dict[int, str] = {32: "~7 decimal digits", 64: "~15 decimal digits"}


def _format_bound(value: int | float) -> str:
    """Format a numeric bound for display.

    Uses ``2^63`` notation for int64-scale values to avoid unreadable
    numbers; otherwise formats with thousands separators for ints.
    """
    if value == _INT64_MIN:
        return "-2^63"
    if value == _INT64_MAX:
        return "2^63-1"
    if isinstance(value, float):
        return str(value)
    return f"{value:,}"


def _format_interval(bounds: Interval) -> str:
    """Format an Interval as a range string, or empty if unconstrained.

    Two inclusive bounds render as ``lower to upper``. All other
    combinations use explicit comparison operators so the
    inclusivity/exclusivity is unambiguous.
    """
    # Interval fields are typed as Supports* protocols; narrow to numeric
    # since we only encounter int/float constraints from the schema.
    ge = cast(_NumericBound, bounds.ge)
    gt = cast(_NumericBound, bounds.gt)
    le = cast(_NumericBound, bounds.le)
    lt = cast(_NumericBound, bounds.lt)

    # Both bounds inclusive: compact "lower to upper" form
    if ge is not None and le is not None:
        return f"{_format_bound(ge)} to {_format_bound(le)}"

    # Any other two-bound combination: use explicit operators
    parts: list[str] = []
    if ge is not None:
        parts.append(f">= {_format_bound(ge)}")
    elif gt is not None:
        parts.append(f"> {_format_bound(gt)}")

    if le is not None:
        parts.append(f"<= {_format_bound(le)}")
    elif lt is not None:
        parts.append(f"< {_format_bound(lt)}")

    return ", ".join(parts)


def _bit_width_key(name: str) -> tuple[str, int]:
    """Sort key: prefix then numeric bit width."""
    prefix = name.rstrip("0123456789")
    digits = name[len(prefix) :]
    return (prefix, int(digits) if digits else 0)


def render_primitives_from_specs(specs: list[PrimitiveSpec]) -> str:
    """Render the primitives.md page from pre-extracted PrimitiveSpecs."""
    template = _get_jinja_env().get_template("primitives.md.jinja2")

    signed_ints: list[dict[str, str | None]] = []
    unsigned_ints: list[dict[str, str | None]] = []
    floats: list[dict[str, str | None]] = []

    for spec in sorted(specs, key=lambda s: _bit_width_key(s.name)):
        if spec.name.startswith(("int", "uint")):
            target = signed_ints if spec.name.startswith("int") else unsigned_ints
            target.append(
                {
                    "name": spec.name,
                    "range": _format_interval(spec.bounds),
                    "description": _sanitize_for_table_cell(spec.description or ""),
                }
            )
        elif spec.name.startswith("float"):
            precision = (
                _FLOAT_PRECISION.get(spec.float_bits, "") if spec.float_bits else ""
            )
            floats.append(
                {
                    "name": spec.name,
                    "precision": precision,
                    "description": _sanitize_for_table_cell(spec.description or ""),
                }
            )

    return template.render(
        signed_ints=signed_ints,
        unsigned_ints=unsigned_ints,
        floats=floats,
    )


def render_geometry_from_values(geometry_type_values: list[str]) -> str:
    """Render the geometry.md page from pre-extracted geometry type values."""
    template = _get_jinja_env().get_template("geometry.md.jinja2")
    geometry_types = ", ".join(f"`{v}`" for v in geometry_type_values)
    return template.render(geometry_types=geometry_types)
