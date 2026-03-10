"""Tests for union type construction."""

import pytest
from overture.schema.core.discovery import filter_models
from overture.schema.core.union import create_union_type_from_models
from pydantic import BaseModel


class TestCreateUnionType:
    """Tests for create_union_type_from_models."""

    def test_creates_type_from_single_theme(self) -> None:
        models = filter_models(theme_names=("buildings",))
        result = create_union_type_from_models(models)
        assert result is not None

    def test_creates_type_from_multiple_themes(self) -> None:
        models = filter_models(theme_names=("buildings", "places"))
        result = create_union_type_from_models(models)
        assert result is not None

    def test_raises_on_empty_models(self) -> None:
        with pytest.raises(ValueError, match="No models provided"):
            create_union_type_from_models({})

    def test_single_model_returns_class_directly(self) -> None:
        models = filter_models(theme_names=("buildings",), type_names=("building",))
        result = create_union_type_from_models(models)
        assert isinstance(result, type) and issubclass(result, BaseModel)
