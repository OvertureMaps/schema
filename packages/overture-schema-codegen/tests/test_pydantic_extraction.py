"""Tests for Pydantic type extraction."""

from overture.schema.codegen.extraction.pydantic_extraction import extract_pydantic_type
from overture.schema.codegen.extraction.specs import PydanticTypeSpec
from pydantic import EmailStr, HttpUrl


class TestExtractPydanticType:
    def test_extracts_http_url(self) -> None:
        spec = extract_pydantic_type(HttpUrl)
        assert isinstance(spec, PydanticTypeSpec)
        assert spec.name == "HttpUrl"
        assert spec.source_type is HttpUrl
        assert spec.source_module == "networks"
        assert spec.description is not None
        assert "http" in spec.description.lower()

    def test_extracts_email_str(self) -> None:
        spec = extract_pydantic_type(EmailStr)
        assert isinstance(spec, PydanticTypeSpec)
        assert spec.name == "EmailStr"
        assert spec.source_type is EmailStr
        assert spec.source_module == "networks"

    def test_admonition_label_filtered_from_description(self) -> None:
        spec = extract_pydantic_type(EmailStr)
        # EmailStr.__doc__ starts with "Info:" (bare admonition label).
        # _usable_description filters this, returning None.
        assert spec.description is None
