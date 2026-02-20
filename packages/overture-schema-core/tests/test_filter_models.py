"""Tests for model filtering."""

import pytest
from overture.schema.core.discovery import ModelKey, filter_models


class TestFilterModels:
    """Tests for filter_models function."""

    @pytest.mark.parametrize(
        "namespace,theme_names,type_names,should_succeed",
        [
            pytest.param("overture", (), (), True, id="overture_namespace"),
            pytest.param(None, ("buildings",), (), True, id="theme_buildings"),
            pytest.param(
                None, ("transportation",), (), True, id="theme_transportation"
            ),
            pytest.param(None, ("buildings", "places"), (), True, id="multiple_themes"),
            pytest.param(None, ("nonexistent",), (), False, id="invalid_theme"),
            pytest.param(None, (), ("building",), True, id="type_building"),
            pytest.param(None, (), ("segment",), True, id="type_segment"),
            pytest.param(None, (), ("building", "place"), True, id="multiple_types"),
            pytest.param(None, (), ("nonexistent",), False, id="invalid_type"),
            pytest.param(
                None,
                ("buildings",),
                ("building",),
                True,
                id="theme_and_type_match",
            ),
            pytest.param(
                None,
                ("buildings",),
                ("segment",),
                False,
                id="theme_and_type_mismatch",
            ),
            pytest.param(None, (), (), True, id="no_filters_all_models"),
        ],
    )
    def test_filter_models_combinations(
        self,
        namespace: str | None,
        theme_names: tuple[str, ...],
        type_names: tuple[str, ...],
        should_succeed: bool,
    ) -> None:
        if should_succeed:
            result = filter_models(namespace, theme_names, type_names)
            assert len(result) > 0
            assert all(isinstance(k, ModelKey) for k in result)
        else:
            with pytest.raises(ValueError, match="No models found"):
                filter_models(namespace, theme_names, type_names)

    def test_case_sensitive(self) -> None:
        result = filter_models(theme_names=("buildings",))
        assert len(result) > 0

        with pytest.raises(ValueError, match="No models found"):
            filter_models(theme_names=("BUILDINGS",))

    def test_namespace_isolation(self) -> None:
        all_models = filter_models()
        overture_models = filter_models(namespace="overture")
        assert len(all_models) >= len(overture_models)
