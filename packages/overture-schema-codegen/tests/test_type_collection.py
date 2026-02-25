"""Tests for type collection module."""

from codegen_test_support import FeatureWithAddress, FeatureWithSources, Instrument
from overture.schema.codegen.model_extraction import expand_model_tree, extract_model
from overture.schema.codegen.specs import (
    EnumSpec,
    ModelSpec,
    NewTypeSpec,
    SupplementarySpec,
)
from overture.schema.codegen.type_collection import collect_all_supplementary_types


class TestCollectAllSupplementarySpecs:
    """Tests for collect_all_supplementary_types returning specs from expanded trees."""

    @staticmethod
    def _expanded_supplementary(
        model_class: type,
    ) -> dict[str, SupplementarySpec]:
        spec = extract_model(model_class)
        expand_model_tree(spec)
        return collect_all_supplementary_types([spec])

    def test_returns_enum_specs(self) -> None:
        result = self._expanded_supplementary(Instrument)

        assert "InstrumentFamily" in result
        assert isinstance(result["InstrumentFamily"], EnumSpec)

    def test_returns_newtype_specs(self) -> None:
        result = self._expanded_supplementary(Instrument)

        assert "HexColor" in result
        assert isinstance(result["HexColor"], NewTypeSpec)

    def test_returns_model_specs_from_expanded_tree(self) -> None:
        result = self._expanded_supplementary(FeatureWithAddress)

        assert "Address" in result
        assert isinstance(result["Address"], ModelSpec)

    def test_collects_transitive_types(self) -> None:
        """Types referenced by sub-models are also collected."""
        result = self._expanded_supplementary(FeatureWithSources)

        # Sources is a semantic NewType; SourceItem is a sub-model
        # referenced transitively via the expanded tree
        assert "Sources" in result
        assert "SourceItem" in result
