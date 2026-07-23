"""Markdown documents a RootModel entry point as a type-alias page.

A RootModel drops out of expression generation but not markdown: it is a
named alias over its bare root value, rendered through the same NewType
page as any other alias. `generate_markdown_pages` takes such aliases
alongside the feature specs it collects from field trees.
"""

from codegen_test_support import TollChargesByVehicleType, Widget, spec_for_model
from overture.schema.codegen.extraction.newtype_extraction import (
    extract_rootmodel_alias,
)
from overture.schema.codegen.markdown.pipeline import generate_markdown_pages

# Widget and the RootModel share the codegen_test_support module, so a single
# schema root covers both; Widget's fields are primitives, pulling in no
# out-of-root supplementary types.
_SCHEMA_ROOT = "codegen_test_support"


def _pages_with_alias() -> list:
    feature = spec_for_model(Widget, entry_point="codegen_test_support:Widget")
    alias = extract_rootmodel_alias(TollChargesByVehicleType)
    return generate_markdown_pages(
        [feature], _SCHEMA_ROOT, external_specs={alias.identity: alias}
    )


def test_rootmodel_alias_produces_a_page() -> None:
    pages = _pages_with_alias()
    alias_page = next(
        (p for p in pages if "# TollChargesByVehicleType" in p.content), None
    )
    assert alias_page is not None


def test_alias_page_renders_as_alias_not_feature() -> None:
    pages = _pages_with_alias()
    alias_page = next(p for p in pages if "# TollChargesByVehicleType" in p.content)

    # The NewType template's "Underlying type:" line, not a feature's field table.
    assert "Underlying type:" in alias_page.content
    assert alias_page.is_model is False
