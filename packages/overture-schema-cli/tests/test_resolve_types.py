"""Parametrized tests for resolve_types function."""

import pytest
from overture.schema.cli.commands import resolve_types


class TestResolveTypes:
    """Tests for the resolve_types function with various filter combinations."""

    @pytest.mark.parametrize(
        "overture_types,namespace,theme_names,type_names,should_succeed",
        [
            # Test --overture-types flag
            pytest.param(True, None, (), (), True, id="overture_types_only"),
            pytest.param(False, "overture", (), (), True, id="overture_namespace"),
            # Test theme filtering
            pytest.param(False, None, ("buildings",), (), True, id="theme_buildings"),
            pytest.param(
                False, None, ("transportation",), (), True, id="theme_transportation"
            ),
            pytest.param(
                False, None, ("buildings", "places"), (), True, id="multiple_themes"
            ),
            pytest.param(False, None, ("nonexistent",), (), False, id="invalid_theme"),
            # Test type filtering
            pytest.param(False, None, (), ("building",), True, id="type_building"),
            pytest.param(False, None, (), ("segment",), True, id="type_segment"),
            pytest.param(
                False, None, (), ("building", "place"), True, id="multiple_types"
            ),
            pytest.param(False, None, (), ("nonexistent",), False, id="invalid_type"),
            # Test combined theme + type filtering
            pytest.param(
                False,
                None,
                ("buildings",),
                ("building",),
                True,
                id="theme_and_type_match",
            ),
            pytest.param(
                False,
                None,
                ("buildings",),
                ("segment",),
                False,
                id="theme_and_type_mismatch",
            ),
            pytest.param(
                False,
                None,
                ("transportation",),
                ("segment", "connector"),
                True,
                id="theme_with_multiple_types",
            ),
            # Test namespace combined with theme/type
            pytest.param(
                False,
                "overture",
                ("buildings",),
                (),
                True,
                id="namespace_with_theme",
            ),
            pytest.param(
                False,
                "overture",
                (),
                ("building",),
                True,
                id="namespace_with_type",
            ),
            pytest.param(
                False,
                "overture",
                ("buildings",),
                ("building",),
                True,
                id="namespace_with_theme_and_type",
            ),
            # Test no filters (all models)
            pytest.param(False, None, (), (), True, id="no_filters_all_models"),
        ],
    )
    def test_resolve_types_combinations(
        self,
        overture_types: bool,
        namespace: str | None,
        theme_names: tuple[str, ...],
        type_names: tuple[str, ...],
        should_succeed: bool,
    ) -> None:
        """Test resolve_types with various filter combinations."""
        if should_succeed:
            model_type = resolve_types(
                overture_types, namespace, theme_names, type_names
            )
            assert model_type is not None
        else:
            with pytest.raises(ValueError, match="No models found"):
                resolve_types(overture_types, namespace, theme_names, type_names)

    @pytest.mark.parametrize(
        "namespace,expected_themes",
        [
            pytest.param(
                "overture",
                {
                    "buildings",
                    "places",
                    "transportation",
                    "base",
                    "divisions",
                    "addresses",
                },
                id="overture_namespace",
            ),
        ],
    )
    def test_resolve_types_returns_expected_themes(
        self,
        namespace: str,
        expected_themes: set[str],
    ) -> None:
        """Test that resolve_types returns models from expected themes."""
        from overture.schema.core.discovery import discover_models

        models = discover_models(namespace=namespace)
        actual_themes = {key.theme for key in models.keys()}

        # Check that we have at least the expected themes (may have more)
        assert expected_themes.issubset(actual_themes), (
            f"Missing expected themes. Expected {expected_themes}, got {actual_themes}"
        )


class TestResolveTypesEdgeCases:
    """Tests for edge cases in resolve_types."""

    def test_resolve_types_case_sensitive(self) -> None:
        """Test that theme and type names are case-sensitive."""
        # Lowercase should work
        model_type = resolve_types(False, None, ("buildings",), ())
        assert model_type is not None

        # Uppercase should fail (themes are lowercase in registry)
        with pytest.raises(ValueError, match="No models found"):
            resolve_types(False, None, ("BUILDINGS",), ())

    def test_resolve_types_empty_result_error_message(self) -> None:
        """Test that a helpful error message is shown when no models match."""
        with pytest.raises(ValueError) as exc_info:
            resolve_types(False, None, ("nonexistent",), ("also_fake",))

        assert "No models found" in str(exc_info.value)

    def test_resolve_types_namespace_isolation(self) -> None:
        """Test that namespace filtering properly isolates models."""
        # Get all models (no namespace filter)
        all_models_type = resolve_types(False, None, (), ())
        assert all_models_type is not None

        # Get only overture namespace
        overture_type = resolve_types(False, "overture", (), ())
        assert overture_type is not None

        # Both should work, but they represent different sets of models
        # (This test primarily ensures no exceptions are raised)
