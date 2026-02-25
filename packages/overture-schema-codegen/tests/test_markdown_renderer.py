"""Tests for Markdown renderer."""

from collections.abc import Callable
from enum import Enum
from pathlib import PurePosixPath
from typing import Annotated, Literal, NewType

import pytest
from annotated_types import Ge, Interval
from codegen_test_support import (
    STR_TYPE,
    CommonNames,
    FeatureBase,
    FeatureWithAddress,
    FeatureWithSources,
    SimpleModel,
    Sources,
    TreeNode,
    Venue,
    make_union_spec,
)
from overture.schema.codegen.example_loader import ExampleRecord
from overture.schema.codegen.link_computation import LinkContext
from overture.schema.codegen.markdown_renderer import (
    _format_constraint,
    _format_example_value,
    _linkify_bare_urls,
    _sanitize_for_table_cell,
    render_enum,
    render_feature,
    render_newtype,
    render_primitives_from_specs,
)
from overture.schema.codegen.model_extraction import expand_model_tree, extract_model
from overture.schema.codegen.newtype_extraction import extract_newtype
from overture.schema.codegen.reverse_references import UsedByEntry, UsedByKind
from overture.schema.codegen.specs import (
    AnnotatedField,
    EnumMemberSpec,
    EnumSpec,
    FieldSpec,
    PrimitiveSpec,
)
from overture.schema.codegen.type_analyzer import ConstraintSource
from overture.schema.system.field_constraint import (
    CountryCodeAlpha2Constraint,
    JsonPointerConstraint,
    UniqueItemsConstraint,
)
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import int32
from overture.schema.system.ref import Id
from overture.schema.system.string import HexColor
from pydantic import BaseModel, Field

_FLAT_MEMBER = EnumMemberSpec(name="FLAT", value="flat", description=None)

_ROOF_SHAPE_SPEC = EnumSpec(
    name="RoofShape",
    description="The shape of the roof.",
    members=[_FLAT_MEMBER],
)


class TestSanitizeForTableCell:
    """Tests for _sanitize_for_table_cell."""

    def test_single_line_unchanged(self) -> None:
        """Single-line text passes through unchanged."""
        assert (
            _sanitize_for_table_cell("A simple description.") == "A simple description."
        )

    def test_single_newline_becomes_space(self) -> None:
        """Single newline within a paragraph becomes a space."""
        assert _sanitize_for_table_cell("Line one.\nLine two.") == "Line one. Line two."

    def test_blank_line_becomes_double_br(self) -> None:
        """Blank line (paragraph break) becomes <br/><br/>."""
        assert (
            _sanitize_for_table_cell("Para one.\n\nPara two.")
            == "Para one.<br/><br/>Para two."
        )

    def test_blank_line_with_whitespace(self) -> None:
        """Blank line containing only whitespace is treated as blank."""
        assert (
            _sanitize_for_table_cell("Para one.\n  \nPara two.")
            == "Para one.<br/><br/>Para two."
        )

    def test_multiple_blank_lines_collapsed(self) -> None:
        """Multiple consecutive blank lines collapse to one <br/><br/>."""
        assert _sanitize_for_table_cell("A.\n\n\nB.") == "A.<br/><br/>B."

    def test_pipe_escaped(self) -> None:
        """Pipe characters escaped to avoid breaking table columns."""
        assert _sanitize_for_table_cell("foo | bar") == "foo \\| bar"

    def test_pipe_and_newline_both_handled(self) -> None:
        """Pipes and newlines handled together."""
        assert _sanitize_for_table_cell("a | b\nc | d") == "a \\| b c \\| d"

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Leading/trailing whitespace stripped."""
        assert _sanitize_for_table_cell("  hello  ") == "hello"


class TestLinkifyBareUrls:
    """Tests for _linkify_bare_urls."""

    def test_www_url_gets_linked(self) -> None:
        """www. URLs become Markdown links with https:// href."""
        assert (
            _linkify_bare_urls("see www.example.com for details")
            == "see [www.example.com](https://www.example.com) for details"
        )

    def test_https_url_gets_linked(self) -> None:
        """https:// URLs become self-referencing Markdown links."""
        assert (
            _linkify_bare_urls("see https://example.com/path")
            == "see [https://example.com/path](https://example.com/path)"
        )

    def test_http_url_gets_linked(self) -> None:
        """http:// URLs become self-referencing Markdown links."""
        assert (
            _linkify_bare_urls("see http://example.com")
            == "see [http://example.com](http://example.com)"
        )

    def test_existing_markdown_link_unchanged(self) -> None:
        """URLs already inside [text](url) are left alone."""
        text = "[example](https://example.com)"
        assert _linkify_bare_urls(text) == text

    def test_text_without_urls_unchanged(self) -> None:
        """Plain text passes through unchanged."""
        assert _linkify_bare_urls("no urls here") == "no urls here"

    def test_url_in_parentheses(self) -> None:
        """URL inside sentence parentheses gets linked."""
        result = _linkify_bare_urls("from the OA (www.openaddresses.io) project")
        assert "[www.openaddresses.io](https://www.openaddresses.io)" in result

    def test_trailing_period_excluded(self) -> None:
        """Trailing sentence punctuation is not part of the URL."""
        assert (
            _linkify_bare_urls("found on https://www.wikidata.org/.")
            == "found on [https://www.wikidata.org/](https://www.wikidata.org/)."
        )

    def test_trailing_comma_excluded(self) -> None:
        """Trailing comma is not part of the URL."""
        assert (
            _linkify_bare_urls("see https://example.com, and more")
            == "see [https://example.com](https://example.com), and more"
        )

    def test_url_in_backtick_code_span_unchanged(self) -> None:
        """URLs inside backtick code spans are not linkified."""
        text = "use `https://example.com` as the base"
        assert _linkify_bare_urls(text) == text

    def test_url_in_double_backtick_code_span_unchanged(self) -> None:
        """URLs inside double-backtick code spans are not linkified."""
        text = "use ``https://example.com/path`` as the base"
        assert _linkify_bare_urls(text) == text

    def test_mixed_code_span_and_bare_url(self) -> None:
        """Code-span URLs preserved while bare URLs are linkified."""
        text = "see `https://a.com` and https://b.com"
        result = _linkify_bare_urls(text)
        assert "`https://a.com`" in result
        assert "[https://b.com](https://b.com)" in result


class TestRenderFeatureBasic:
    """Tests for render_feature with basic models."""

    def test_renders_title_from_model_name(self) -> None:
        """Should render model name as H1 title."""
        spec = extract_model(SimpleModel)
        result = render_feature(spec)

        assert "# SimpleModel" in result

    def test_renders_description_from_docstring(self) -> None:
        """Should render model docstring as description."""

        class DescribedModel(BaseModel):
            """This is the model description."""

            value: int

        spec = extract_model(DescribedModel)
        result = render_feature(spec)

        assert "This is the model description." in result

    def test_renders_fields_section(self) -> None:
        """Should include Fields section header."""

        class ModelWithField(BaseModel):
            """Model with a field."""

            name: str

        spec = extract_model(ModelWithField)
        result = render_feature(spec)

        assert "## Fields" in result

    def test_renders_field_table_header(self) -> None:
        """Should render field table with proper headers."""

        class ModelWithField(BaseModel):
            """Model with a field."""

            name: str

        spec = extract_model(ModelWithField)
        result = render_feature(spec)

        assert "| Name | Type | Description |" in result
        assert "| -----: | :----: | ------------- |" in result


class TestRenderFeatureFieldTable:
    """Tests for field table rendering."""

    def test_renders_required_field(self) -> None:
        """Should render required field without (optional) suffix."""

        class ModelWithRequired(BaseModel):
            """Model with required field."""

            name: str = Field(description="The name")

        spec = extract_model(ModelWithRequired)
        result = render_feature(spec)

        # Should have backtick-quoted field name
        assert "| `name` |" in result
        # Type should be string without optional
        assert "| `string` |" in result or "string" in result
        # Description should be present
        assert "The name" in result

    def test_renders_optional_field(self) -> None:
        """Should render optional field with (optional) suffix."""

        class ModelWithOptional(BaseModel):
            """Model with optional field."""

            nickname: str | None = Field(None, description="Optional nickname")

        spec = extract_model(ModelWithOptional)
        result = render_feature(spec)

        assert "| `nickname` |" in result
        assert "(optional)" in result
        assert "Optional nickname" in result

    def test_renders_typed_fields(self) -> None:
        """Should render field types correctly."""

        class ModelWithTypes(BaseModel):
            """Model with various types."""

            count: int
            price: float
            active: bool

        spec = extract_model(ModelWithTypes)
        result = render_feature(spec)

        # Check that fields are present (exact type format may vary)
        assert "`count`" in result
        assert "`price`" in result
        assert "`active`" in result

    def test_multiline_description_sanitized_in_table(self) -> None:
        """Multiline field description rendered with <br/> in table cell."""

        class ModelWithMultilineDesc(BaseModel):
            """Model."""

            name: str = Field(description="First line.\n\nSecond paragraph.")

        spec = extract_model(ModelWithMultilineDesc)
        result = render_feature(spec)

        assert "First line.<br/><br/>Second paragraph." in result
        # The table should not be broken by a blank line
        lines = result.splitlines()
        table_start = next(i for i, line in enumerate(lines) if "| Name |" in line)
        for i in range(table_start, len(lines)):
            if lines[i].strip() == "":
                break
            assert lines[i].startswith("|"), f"Table broken at line {i}: {lines[i]}"


class TestRenderFeatureWithThemeType:
    """Tests for rendering Feature-like models with theme/type."""

    def test_renders_theme_and_type_fields(self) -> None:
        """Should render theme and type as Literal fields."""

        class Place(FeatureBase[Literal["places"], Literal["place"]]):
            """A place feature."""

            name: str

        spec = extract_model(Place)
        result = render_feature(spec)

        # Theme and type should appear somewhere in output
        assert "places" in result
        assert "place" in result


class TestRenderFeatureLiteralField:
    """Tests for rendering Literal-typed fields."""

    def test_literal_field_renders_as_quoted_value(self) -> None:
        """Literal field should render as quoted string in backticks."""

        class TestFeature(FeatureBase[Literal["test_theme"], Literal["test_type"]]):
            """Test feature."""

            name: str

        spec = extract_model(TestFeature)
        result = render_feature(spec)

        assert '| `"test_theme"` |' in result
        assert '| `"test_type"` |' in result


class TestRenderFeatureNewTypeDisplay:
    """Tests for NewType rendering in Markdown."""

    def test_newtype_wrapping_list_renders_name_with_list_qualifier(
        self,
    ) -> None:
        """NewType wrapping a list renders as name with (list, optional)."""

        class Item(BaseModel):
            value: str

        TestSources = NewType(
            "TestSources", Annotated[list[Item], UniqueItemsConstraint()]
        )

        class ModelWithSources(BaseModel):
            """Model with sources."""

            sources: TestSources | None = None

        spec = extract_model(ModelWithSources)
        expand_model_tree(spec)
        result = render_feature(spec)

        assert "`TestSources`" in result
        assert "(list, optional)" in result

    def test_hex_color_renders_as_newtype_name(self) -> None:
        """HexColor (unregistered NewType) renders as code-formatted name."""

        class ModelWithColor(BaseModel):
            """Model with color."""

            color: HexColor | None = None

        spec = extract_model(ModelWithColor)
        result = render_feature(spec)

        assert "`HexColor`" in result
        assert "(optional)" in result

    def test_registered_primitive_renders_through_registry(self) -> None:
        """Registered primitive (int32) renders via registry, not as NewType link."""

        class ModelWithCount(BaseModel):
            """Model with count."""

            count: int32

        spec = extract_model(ModelWithCount)
        result = render_feature(spec)

        assert "| `int32` |" in result
        # Should NOT be linked
        assert "](int32.md)" not in result

    def test_plain_str_renders_as_string(self) -> None:
        """Plain str field renders as 'string'."""

        class ModelWithName(BaseModel):
            """Model with name."""

            name: str

        spec = extract_model(ModelWithName)
        result = render_feature(spec)

        assert "| `string` |" in result

    def test_enum_renders_as_code_without_context(self) -> None:
        """Enum fields render as inline code without LinkContext."""

        class Status(str, Enum):
            ACTIVE = "active"

        class ModelWithEnum(BaseModel):
            """Model with enum."""

            status: Status

        spec = extract_model(ModelWithEnum)
        result = render_feature(spec)

        assert "| `Status` |" in result

    def test_model_field_renders_as_code_without_context(self) -> None:
        """BaseModel field renders as inline code without LinkContext."""

        class Inner(BaseModel):
            value: str

        class Outer(BaseModel):
            """Model with nested model."""

            inner: Inner

        spec = extract_model(Outer)
        expand_model_tree(spec)
        result = render_feature(spec)

        assert "| `Inner` |" in result


class TestRenderFeatureInlineExpansion:
    """Tests for inline expansion of nested model fields."""

    def test_direct_model_fields_expanded_with_dot_prefix(self) -> None:
        """Direct model field expands sub-fields with dot notation."""
        spec = extract_model(FeatureWithAddress)
        expand_model_tree(spec)
        result = render_feature(spec)

        assert "| `address.street` |" in result
        assert "| `address.city` |" in result
        assert "| `address.zip_code` |" in result

    def test_list_of_model_fields_expanded_with_bracket_dot_prefix(self) -> None:
        """List-of-model field expands sub-fields with []. notation."""
        spec = extract_model(FeatureWithSources)
        expand_model_tree(spec)
        result = render_feature(spec)

        assert "| `sources[]` |" in result
        assert "| `sources[].dataset` |" in result

    def test_cycle_detection_prevents_infinite_recursion(self) -> None:
        """Recursive model emits parent row but does not recurse."""
        spec = extract_model(TreeNode)
        expand_model_tree(spec)
        result = render_feature(spec)

        # The parent field row appears
        assert "| `parent` |" in result
        # But no recursion into parent.label
        assert "parent.label" not in result

    def test_primitive_field_unchanged(self) -> None:
        """Primitive fields produce a single row without expansion."""
        spec = extract_model(SimpleModel)
        result = render_feature(spec)

        lines = [line for line in result.splitlines() if "| `name` |" in line]
        assert len(lines) == 1

    def test_parent_row_preserved_before_expansion(self) -> None:
        """The parent field row still appears before expanded sub-fields."""
        spec = extract_model(FeatureWithAddress)
        expand_model_tree(spec)
        result = render_feature(spec)

        # Parent row for 'address' itself appears
        assert "| `address` |" in result
        # And it appears before the expanded fields
        lines = result.splitlines()
        address_line = next(
            i for i, line in enumerate(lines) if "| `address` |" in line
        )
        street_line = next(
            i for i, line in enumerate(lines) if "| `address.street` |" in line
        )
        assert address_line < street_line


class TestRenderFeatureConstraints:
    """Tests for model-level constraint rendering in feature pages."""

    def test_venue_has_constraints_section(self) -> None:
        """Venue's @require_any_of renders as a Constraints section."""
        spec = extract_model(Venue)
        result = render_feature(spec)

        assert "## Constraints" in result
        assert "At least one of `name`, `description` must be set" in result

    def test_constraints_section_between_fields_and_examples(self) -> None:
        """Constraints section appears after Fields, before Examples."""
        spec = extract_model(Venue)
        examples = [ExampleRecord(rows=[("name", "test")])]
        result = render_feature(spec, examples=examples)

        lines = result.splitlines()
        fields_line = next(i for i, line in enumerate(lines) if "## Fields" in line)
        constraints_line = next(
            i for i, line in enumerate(lines) if "## Constraints" in line
        )
        examples_line = next(i for i, line in enumerate(lines) if "## Examples" in line)

        assert fields_line < constraints_line < examples_line

    def test_no_constraints_section_without_constraints(self) -> None:
        """Models without model-level constraints omit Constraints section."""

        class Plain(BaseModel):
            """Plain model."""

            name: str

        spec = extract_model(Plain)
        result = render_feature(spec)

        assert "## Constraints" not in result

    def test_no_constraints_section_with_only_no_extra_fields(self) -> None:
        """Model with only @no_extra_fields omits Constraints section."""

        @no_extra_fields
        class Strict(BaseModel):
            """Strict model."""

            name: str

        spec = extract_model(Strict)
        result = render_feature(spec)

        assert "## Constraints" not in result


class TestRenderFeatureConstraintNotes:
    """Tests for inline constraint notes in field description cells."""

    def test_venue_name_field_includes_constraint_note(self) -> None:
        """Venue's name field description cell includes constraint note in italics."""
        spec = extract_model(Venue)
        result = render_feature(spec)

        # Find the row for 'name' field
        lines = result.splitlines()
        name_line = next(line for line in lines if "| `name` |" in line)
        assert "Venue name" in name_line
        assert "*At least one of `name`, `description` must be set*" in name_line
        assert "<br/>" in name_line

    def test_field_with_no_description_gets_constraint_note(self) -> None:
        """Field with no existing description still gets the constraint note."""
        spec = extract_model(Venue)
        result = render_feature(spec)

        # description field on Venue has no Field(description=...)
        lines = result.splitlines()
        desc_line = next(line for line in lines if "| `description` |" in line)
        assert "*At least one of `name`, `description` must be set*" in desc_line


class TestRenderFeatureFieldConstraints:
    """Tests for field-level constraint annotation from TypeInfo."""

    def test_venue_geometry_shows_allowed_types(self) -> None:
        """Venue's geometry field shows GeometryTypeConstraint as a note."""
        spec = extract_model(Venue)
        expand_model_tree(spec)
        result = render_feature(spec)

        lines = result.splitlines()
        geo_line = next(line for line in lines if "| `geometry` |" in line)
        assert "*Allowed geometry types: Point, Polygon*" in geo_line

    def test_venue_reference_links_when_context_available(self) -> None:
        """Reference constraint links the target type when LinkContext has the page."""
        spec = extract_model(Venue)
        expand_model_tree(spec)
        ctx = LinkContext(
            page_path=PurePosixPath("music/venue.md"),
            registry={"Instrument": PurePosixPath("music/instrument.md")},
        )
        result = render_feature(spec, link_ctx=ctx)

        lines = result.splitlines()
        ref_line = next(line for line in lines if "| `resident_ensemble` |" in line)
        assert "[`Instrument`](instrument.md)" in ref_line
        assert "belongs to" in ref_line

    def test_venue_reference_unlinked_without_context(self) -> None:
        """Reference constraint renders as plain code when no LinkContext."""
        spec = extract_model(Venue)
        expand_model_tree(spec)
        result = render_feature(spec)

        lines = result.splitlines()
        ref_line = next(line for line in lines if "| `resident_ensemble` |" in line)
        assert "References `Instrument`" in ref_line
        assert "belongs to" in ref_line


class TestRenderEnumBasic:
    """Tests for render_enum with simple enums."""

    def test_renders_title_from_enum_name(self) -> None:
        """Should render enum name as H1 title."""
        result = render_enum(_ROOF_SHAPE_SPEC)

        assert "# RoofShape" in result

    def test_renders_description_from_docstring(self) -> None:
        """Should render enum docstring as description."""
        result = render_enum(_ROOF_SHAPE_SPEC)

        assert "The shape of the roof." in result

    def test_renders_values_section(self) -> None:
        """Should include Values section header."""
        result = render_enum(_ROOF_SHAPE_SPEC)

        assert "## Values" in result

    def test_renders_values_as_bullet_list(self) -> None:
        """Should render each value as a bullet point."""
        spec = EnumSpec(
            name="RoofShape",
            description="The shape of the roof.",
            members=[
                EnumMemberSpec(name="FLAT", value="flat", description=None),
                EnumMemberSpec(name="GABLED", value="gabled", description=None),
                EnumMemberSpec(name="DOME", value="dome", description=None),
            ],
        )

        result = render_enum(spec)

        assert "- `flat`" in result
        assert "- `gabled`" in result
        assert "- `dome`" in result


class TestRenderEnumDocumented:
    """Tests for render_enum with DocumentedEnum (per-value descriptions)."""

    def test_renders_member_descriptions(self) -> None:
        """Should render per-value descriptions after the value."""
        spec = EnumSpec(
            name="Side",
            description="The side on which something appears.",
            members=[
                EnumMemberSpec(
                    name="LEFT", value="left", description="On the left side"
                ),
                EnumMemberSpec(
                    name="RIGHT", value="right", description="On the right side"
                ),
            ],
        )

        result = render_enum(spec)

        assert "- `left` - On the left side" in result
        assert "- `right` - On the right side" in result

    def test_renders_mixed_documented_undocumented(self) -> None:
        """Should handle mix of documented and undocumented members."""
        spec = EnumSpec(
            name="ConnectionState",
            description="Connection states.",
            members=[
                EnumMemberSpec(name="CONNECTED", value="connected", description=None),
                EnumMemberSpec(
                    name="QUIESCING",
                    value="quiescing",
                    description="Gracefully shutting down",
                ),
            ],
        )

        result = render_enum(spec)

        # Undocumented: just the value
        assert "- `connected`" in result
        # Documented: value + description
        assert "- `quiescing` - Gracefully shutting down" in result


class TestRenderEnumNoDescription:
    """Tests for enums without class docstrings."""

    def test_enum_without_description(self) -> None:
        """Should render enum without description section when None."""
        spec = EnumSpec(
            name="SimpleEnum",
            description=None,
            members=[
                EnumMemberSpec(name="A", value="a", description=None),
                EnumMemberSpec(name="B", value="b", description=None),
            ],
        )

        result = render_enum(spec)

        # Should still have title and values
        assert "# SimpleEnum" in result
        assert "## Values" in result
        assert "- `a`" in result
        assert "- `b`" in result
        # Should not have empty lines where description would be
        lines = result.strip().split("\n")
        # Title should be followed by blank line then Values header
        assert lines[0] == "# SimpleEnum"


class TestRenderNewType:
    """Tests for render_newtype."""

    def test_renders_title(self) -> None:
        """Should render NewType name as H1 title."""
        spec = extract_newtype(HexColor)
        result = render_newtype(spec)

        assert "# HexColor" in result

    def test_renders_underlying_type(self) -> None:
        """Should show the resolved underlying type below the description."""
        spec = extract_newtype(HexColor)
        result = render_newtype(spec)

        assert "# HexColor\n" in result
        assert "Underlying type: `string`" in result

    def test_renders_constraints(self) -> None:
        """Should render constraints section with description and pattern."""
        spec = extract_newtype(HexColor)
        result = render_newtype(spec)

        assert "## Constraints" in result
        assert "Allows only hexadecimal color codes" in result
        assert "`HexColorConstraint`" in result
        assert "pattern:" in result

    def test_renders_id_with_provenance_without_link(self) -> None:
        """Id page shows constraints without provenance links when no context."""
        spec = extract_newtype(Id)
        result = render_newtype(spec)

        assert "# Id" in result
        assert "NoWhitespaceConstraint" in result
        # No link without LinkContext
        assert "no_whitespace_string.md" not in result

    def test_builtin_underlying_type_not_linked(self) -> None:
        """Built-in underlying type (string) stays in plain backticks."""
        spec = extract_newtype(HexColor)
        result = render_newtype(spec)

        assert "Underlying type: `string`" in result

    def test_list_model_underlying_type_without_context(self) -> None:
        """List-of-model underlying type renders without link when no context."""
        spec = extract_newtype(Sources)
        result = render_newtype(spec)

        assert "Underlying type: `list<SourceItem>`" in result

    def test_dict_underlying_types_without_context(self) -> None:
        """Dict key/value NewTypes render without links when no context."""
        spec = extract_newtype(CommonNames)
        result = render_newtype(spec)

        assert "map<LanguageTag, StrippedString>" in result


class TestPlacementAwareLinks:
    """Tests for rendering with LinkContext for cross-directory links."""

    def test_feature_links_to_shared_type_via_registry(self) -> None:
        """Feature in theme subdir links to shared type in types/ dir."""

        class ModelWithColor(BaseModel):
            """Model with color."""

            color: HexColor | None = None

        spec = extract_model(ModelWithColor)
        page_path = PurePosixPath("buildings/building/building.md")
        registry = {
            "HexColor": PurePosixPath("types/strings/hex_color.md"),
        }
        ctx = LinkContext(page_path, registry)

        result = render_feature(spec, link_ctx=ctx)

        assert "[`HexColor`](../../types/strings/hex_color.md)" in result

    def test_feature_links_to_theme_level_type(self) -> None:
        """Feature in subdir links to type at theme level."""

        class RoofShape(str, Enum):
            FLAT = "flat"

        class ModelWithRoof(BaseModel):
            """Model with roof."""

            roof: RoofShape

        spec = extract_model(ModelWithRoof)
        page_path = PurePosixPath("buildings/building/building.md")
        registry = {
            "RoofShape": PurePosixPath("buildings/roof_shape.md"),
        }
        ctx = LinkContext(page_path, registry)

        result = render_feature(spec, link_ctx=ctx)

        assert "[`RoofShape`](../roof_shape.md)" in result

    def test_feature_links_to_sibling_in_same_subdir(self) -> None:
        """Feature links to type in its own subdirectory."""

        class BuildingClass(str, Enum):
            RESIDENTIAL = "residential"

        class ModelWithClass(BaseModel):
            """Model."""

            building_class: BuildingClass

        spec = extract_model(ModelWithClass)
        page_path = PurePosixPath("buildings/building/building.md")
        registry = {
            "BuildingClass": PurePosixPath("buildings/building/building_class.md"),
        }
        ctx = LinkContext(page_path, registry)

        result = render_feature(spec, link_ctx=ctx)

        assert "[`BuildingClass`](building_class.md)" in result

    def test_without_context_renders_as_code(self) -> None:
        """Without LinkContext, types render as inline code (no link)."""

        class ModelWithColor(BaseModel):
            """Model with color."""

            color: HexColor | None = None

        spec = extract_model(ModelWithColor)
        result = render_feature(spec)

        assert "`HexColor`" in result
        assert "hex_color.md" not in result

    def test_newtype_underlying_type_linked_via_registry(self) -> None:
        """NewType header links underlying model type through placement registry."""
        spec = extract_newtype(Sources)
        page_path = PurePosixPath("types/references/sources.md")
        registry = {
            "SourceItem": PurePosixPath("types/references/source_item.md"),
        }
        ctx = LinkContext(page_path, registry)

        result = render_newtype(spec, link_ctx=ctx)

        assert "[`SourceItem`](source_item.md)" in result

    def test_newtype_underlying_type_not_linked_when_absent(self) -> None:
        """Underlying type stays backtick-only when missing from registry."""
        spec = extract_newtype(Sources)
        page_path = PurePosixPath("types/references/sources.md")
        registry: dict[str, PurePosixPath] = {}
        ctx = LinkContext(page_path, registry)

        result = render_newtype(spec, link_ctx=ctx)

        assert "`list<SourceItem>`" in result
        assert "[`SourceItem`]" not in result

    def test_newtype_provenance_link_uses_registry(self) -> None:
        """NewType provenance links resolve through placement registry."""
        spec = extract_newtype(Id)
        page_path = PurePosixPath("types/references/id.md")
        registry = {
            "NoWhitespaceString": PurePosixPath(
                "types/strings/no_whitespace_string.md"
            ),
        }
        ctx = LinkContext(page_path, registry)

        result = render_newtype(spec, link_ctx=ctx)

        assert "../strings/no_whitespace_string.md" in result


class TestFormatExampleValue:
    """Tests for _format_example_value."""

    def test_none_renders_as_null(self) -> None:
        """None renders as backtick-quoted null."""

        assert _format_example_value(None) == "`null`"

    def test_string_null_renders_with_backticks(self) -> None:
        """String 'null' renders as a backtick-wrapped string."""

        assert _format_example_value("null") == "`null`"

    def test_bool_true_renders_lowercase(self) -> None:
        """Boolean True renders as backtick-quoted lowercase true."""

        assert _format_example_value(True) == "`true`"

    def test_bool_false_renders_lowercase(self) -> None:
        """Boolean False renders as backtick-quoted lowercase false."""

        assert _format_example_value(False) == "`false`"

    def test_empty_string_renders_empty(self) -> None:
        """Empty string renders as empty string."""

        assert _format_example_value("") == ""

    def test_short_string_has_backticks(self) -> None:
        """Non-empty strings render with backticks."""

        assert _format_example_value("OpenStreetMap") == "`OpenStreetMap`"

    def test_long_string_truncated(self) -> None:
        """Strings longer than 100 chars are truncated with ellipsis."""

        long = "x" * 150
        result = _format_example_value(long)
        assert result == f"`{'x' * 100}...`"

    def test_integer_has_backticks(self) -> None:
        """Integers render with backticks."""

        assert _format_example_value(42) == "`42`"
        assert _format_example_value(0) == "`0`"
        assert _format_example_value(-17) == "`-17`"

    def test_float_has_backticks(self) -> None:
        """Floats render with backticks."""

        assert _format_example_value(3.14) == "`3.14`"
        assert _format_example_value(-2.5) == "`-2.5`"

    def test_list_renders_comma_separated(self) -> None:
        """Lists render as backtick-wrapped comma-separated values."""

        assert _format_example_value([1, 2, 3]) == "`[1, 2, 3]`"
        assert _format_example_value(["a", "b"]) == "`[a, b]`"
        assert _format_example_value([]) == "`[]`"

    def test_pipe_character_not_escaped_in_backticks(self) -> None:
        """Pipe characters need no escaping inside backticks."""

        assert _format_example_value("foo|bar") == "`foo|bar`"
        assert _format_example_value("a|b|c") == "`a|b|c`"


class TestRenderFeatureWithExamples:
    """Tests for render_feature with examples support."""

    def test_accepts_examples_parameter(self) -> None:
        """render_feature accepts examples parameter."""
        spec = extract_model(SimpleModel)
        examples = [ExampleRecord(rows=[("name", "test")])]

        # Should not raise
        result = render_feature(spec, examples=examples)
        assert "# SimpleModel" in result

    def test_renders_single_example_without_heading(self) -> None:
        """Single example renders without 'Example 1' heading."""

        class ModelWithCount(BaseModel):
            """A simple model."""

            name: str
            count: int

        spec = extract_model(ModelWithCount)
        examples = [ExampleRecord(rows=[("name", "test"), ("count", 42)])]

        result = render_feature(spec, examples=examples)
        assert "## Examples" in result
        assert "| Column | Value |" in result
        assert "| `name` | `test` |" in result
        assert "| `count` | `42` |" in result
        # Should NOT have "Example 1" heading
        assert "### Example 1" not in result

    def test_renders_multiple_examples_with_headings(self) -> None:
        """Multiple examples render with 'Example N' headings."""
        spec = extract_model(SimpleModel)
        examples = [
            ExampleRecord(rows=[("name", "first")]),
            ExampleRecord(rows=[("name", "second")]),
        ]

        result = render_feature(spec, examples=examples)
        assert "## Examples" in result
        assert "### Example 1" in result
        assert "### Example 2" in result
        assert "| `name` | `first` |" in result
        assert "| `name` | `second` |" in result

    def test_formats_example_values(self) -> None:
        """Example values are formatted using _format_example_value."""

        class TestModel(BaseModel):
            """Test model."""

            text: str
            count: int
            active: bool
            optional: str | None

        spec = extract_model(TestModel)
        examples = [
            ExampleRecord(
                rows=[
                    ("text", "hello"),
                    ("count", 42),
                    ("active", True),
                    ("optional", None),
                ]
            )
        ]

        result = render_feature(spec, examples=examples)
        # String with backticks
        assert "| `text` | `hello` |" in result
        # Number with backticks
        assert "| `count` | `42` |" in result
        # Boolean with backticks, lowercase
        assert "| `active` | `true` |" in result
        # None as null
        assert "| `optional` | `null` |" in result

    def test_no_examples_omits_section(self) -> None:
        """When examples is None, Examples section is not rendered."""
        spec = extract_model(SimpleModel)
        result = render_feature(spec, examples=None)

        assert "## Examples" not in result

    def test_empty_examples_list_omits_section(self) -> None:
        """When examples is empty list, Examples section is not rendered."""
        spec = extract_model(SimpleModel)
        result = render_feature(spec, examples=[])

        assert "## Examples" not in result


class TestRenderPrimitivesPage:
    """Tests for the aggregate primitives page."""

    def test_contains_title(self, primitives_markdown: str) -> None:
        assert "# Primitive Types" in primitives_markdown

    def test_contains_signed_integers(self, primitives_markdown: str) -> None:
        assert "| `int8` |" in primitives_markdown
        assert "| `int16` |" in primitives_markdown
        assert "| `int32` |" in primitives_markdown
        assert "| `int64` |" in primitives_markdown

    def test_contains_unsigned_integers(self, primitives_markdown: str) -> None:
        assert "| `uint8` |" in primitives_markdown
        assert "| `uint16` |" in primitives_markdown
        assert "| `uint32` |" in primitives_markdown

    def test_contains_floats(self, primitives_markdown: str) -> None:
        assert "| `float32` |" in primitives_markdown
        assert "| `float64` |" in primitives_markdown

    def test_ranges_match_schema_constraints(self, primitives_markdown: str) -> None:
        """Range strings derive from ge/le constraints in the schema."""
        assert "-128 to 127" in primitives_markdown
        assert "-32,768 to 32,767" in primitives_markdown
        assert "-2,147,483,648 to 2,147,483,647" in primitives_markdown
        assert "-2^63 to 2^63-1" in primitives_markdown
        assert "0 to 255" in primitives_markdown
        assert "0 to 65,535" in primitives_markdown
        assert "0 to 4,294,967,295" in primitives_markdown

    def test_descriptions_from_docstrings(self, primitives_markdown: str) -> None:
        """Descriptions derive from first line of NewType docstrings."""
        assert "Portable 8-bit signed integer." in primitives_markdown
        assert "Portable 16-bit unsigned integer." in primitives_markdown
        assert "Portable IEEE 32-bit floating point number." in primitives_markdown

    def test_float_precision(self, primitives_markdown: str) -> None:
        """Float entries show IEEE 754 precision."""
        assert "~7 decimal digits" in primitives_markdown
        assert "~15 decimal digits" in primitives_markdown

    def test_pipe_in_description_escaped(self) -> None:
        """Pipe characters in primitive descriptions are escaped."""
        specs = [
            PrimitiveSpec(
                name="int8",
                description="Range: -128 | 127",
                bounds=Interval(ge=-128, le=127),
            ),
        ]
        result = render_primitives_from_specs(specs)
        assert "Range: -128 \\| 127" in result


class TestRenderGeometryPage:
    """Tests for the aggregate geometry page."""

    def test_contains_title(self, geometry_markdown: str) -> None:
        assert "# Geometry Types" in geometry_markdown

    def test_contains_geometry_types(self, geometry_markdown: str) -> None:
        assert "Geometry" in geometry_markdown
        assert "BBox" in geometry_markdown
        assert "GeometryType" in geometry_markdown

    def test_lists_geometry_type_values(self, geometry_markdown: str) -> None:
        assert "`point`" in geometry_markdown or "`POINT`" in geometry_markdown


class TestRenderUnionTemplate:
    """Tests for UnionSpec template rendering with synthetic specs."""

    def test_shared_fields_have_no_variant_tag(self) -> None:
        """Shared fields render without variant annotation."""
        spec = make_union_spec(
            description="A test union.",
            annotated_fields=[
                AnnotatedField(
                    field_spec=FieldSpec(
                        name="id",
                        type_info=STR_TYPE,
                        description="ID",
                        is_required=True,
                    ),
                    variant_sources=None,
                ),
            ],
        )
        result = render_feature(spec)
        assert "| `id` |" in result
        assert "*(" not in result  # no variant tag

    def test_variant_fields_have_inline_tag(self) -> None:
        """Variant-specific fields get *(Variant)* tag."""
        spec = make_union_spec(
            name="Segment",
            annotated_fields=[
                AnnotatedField(
                    field_spec=FieldSpec(
                        name="speed_limit",
                        type_info=STR_TYPE,
                        description=None,
                        is_required=False,
                    ),
                    variant_sources=("RoadSegment",),
                ),
            ],
        )
        result = render_feature(spec)
        assert "| `speed_limit` *(Road)* |" in result


class TestFormatConstraintDisplay:
    """Tests for FieldConstraint display with on-demand description/pattern extraction."""

    def test_description_and_pattern(self) -> None:
        """Constraint with docstring and pattern renders both."""
        cs = ConstraintSource(source=None, constraint=CountryCodeAlpha2Constraint())
        result = _format_constraint(cs, "CountryCodeAlpha2")
        assert "Allows only ISO 3166-1 alpha-2 country codes." in result.display
        assert "`CountryCodeAlpha2Constraint`" in result.display
        assert "pattern: `^[A-Z]{2}$`" in result.display

    def test_description_without_pattern(self) -> None:
        """Constraint with docstring but no pattern renders description only."""
        cs = ConstraintSource(source=None, constraint=JsonPointerConstraint())
        result = _format_constraint(cs, "JsonPointer")
        assert "Allows only valid JSON Pointer values (RFC 6901)." in result.display
        assert "`JsonPointerConstraint`" in result.display
        assert "pattern" not in result.display

    def test_no_description_falls_through(self) -> None:
        """Plain string metadata has no docstring and falls through."""
        cs = ConstraintSource(source=None, constraint="plain string metadata")
        result = _format_constraint(cs, "SomeType")
        assert result.display == "`plain string metadata`"

    def test_annotated_types_uses_operator_notation_not_docstring(self) -> None:
        """annotated-types constraints use operator notation, not their __doc__."""
        cs = ConstraintSource(source=None, constraint=Ge(ge=0))
        result = _format_constraint(cs, "SomeType")
        assert result.display == "`≥ 0`"
        assert "Ge(ge=x)" not in result.display

    def test_constraint_class_not_linked(self) -> None:
        """Constraint class name stays in backticks (no pages generated for constraints)."""
        cs = ConstraintSource(source=None, constraint=CountryCodeAlpha2Constraint())
        result = _format_constraint(cs, "CountryCodeAlpha2")
        assert "`CountryCodeAlpha2Constraint`" in result.display
        assert "[`CountryCodeAlpha2Constraint`](" not in result.display


def _feature_spec() -> object:
    return extract_model(SimpleModel)


def _enum_spec() -> object:
    return _ROOF_SHAPE_SPEC


def _newtype_spec() -> object:
    return extract_newtype(HexColor)


_USED_BY_CASES = [
    pytest.param(_feature_spec, render_feature, id="feature"),
    pytest.param(_enum_spec, render_enum, id="enum"),
    pytest.param(_newtype_spec, render_newtype, id="newtype"),
]


class TestUsedByRendering:
    """Tests for rendering 'Used By' section across all render functions."""

    @pytest.mark.parametrize(("spec_factory", "render_fn"), _USED_BY_CASES)
    def test_entries_render_without_links_when_no_context(
        self,
        spec_factory: Callable[[], object],
        render_fn: Callable[..., str],
    ) -> None:
        """Without LinkContext, 'Used By' entries render as inline code."""
        used_by = [
            UsedByEntry(name="Building", kind=UsedByKind.MODEL),
            UsedByEntry(name="BuildingId", kind=UsedByKind.NEWTYPE),
        ]

        result = render_fn(spec_factory(), used_by=used_by)

        assert "## Used By" in result
        assert "- `Building`" in result
        assert "- `BuildingId`" in result

    @pytest.mark.parametrize(
        ("spec_factory", "render_fn", "page_path", "expected_link"),
        [
            pytest.param(
                _feature_spec,
                render_feature,
                PurePosixPath("types/strings/hex_color.md"),
                "../../buildings/building/building.md",
                id="feature",
            ),
            pytest.param(
                _enum_spec,
                render_enum,
                PurePosixPath("buildings/roof_shape.md"),
                "building/building.md",
                id="enum",
            ),
            pytest.param(
                _newtype_spec,
                render_newtype,
                PurePosixPath("types/strings/hex_color.md"),
                "../../buildings/building/building.md",
                id="newtype",
            ),
        ],
    )
    def test_link_context_uses_registry(
        self,
        spec_factory: Callable[[], object],
        render_fn: Callable[..., str],
        page_path: PurePosixPath,
        expected_link: str,
    ) -> None:
        """Used-by entries resolve links through placement registry."""
        registry = {
            "Building": PurePosixPath("buildings/building/building.md"),
        }
        ctx = LinkContext(page_path, registry)
        used_by = [UsedByEntry(name="Building", kind=UsedByKind.MODEL)]

        result = render_fn(spec_factory(), link_ctx=ctx, used_by=used_by)

        assert "## Used By" in result
        assert f"[`Building`]({expected_link})" in result

    @pytest.mark.parametrize(("spec_factory", "render_fn"), _USED_BY_CASES)
    def test_no_used_by_omits_section(
        self,
        spec_factory: Callable[[], object],
        render_fn: Callable[..., str],
    ) -> None:
        """When used_by is None, 'Used By' section is not rendered."""
        result = render_fn(spec_factory(), used_by=None)

        assert "## Used By" not in result

    @pytest.mark.parametrize(("spec_factory", "render_fn"), _USED_BY_CASES)
    def test_empty_used_by_omits_section(
        self,
        spec_factory: Callable[[], object],
        render_fn: Callable[..., str],
    ) -> None:
        """When used_by is empty list, 'Used By' section is not rendered."""
        result = render_fn(spec_factory(), used_by=[])

        assert "## Used By" not in result
