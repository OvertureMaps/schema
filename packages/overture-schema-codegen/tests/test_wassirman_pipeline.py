"""Tests for the wassirman pipeline."""

from typing import Literal

import pytest
import yaml
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.wassirman.ir import ValidationIR
from overture.schema.codegen.wassirman.pipeline import generate_validation_ir
from pydantic import BaseModel


class TinyModel(BaseModel):
    theme: Literal["test"] = "test"
    type: Literal["tiny"] = "tiny"
    id: str


@pytest.fixture
def tiny_ir() -> ValidationIR:
    spec = extract_model(TinyModel)
    return generate_validation_ir([spec])


def test_generate_returns_validation_ir(tiny_ir: ValidationIR) -> None:
    assert tiny_ir.version == "1"
    assert len(tiny_ir.datasets) == 1
    assert tiny_ir.datasets[0].name == "tiny"


def test_source_model_fqn(tiny_ir: ValidationIR) -> None:
    assert "TinyModel" in tiny_ir.datasets[0].source_model


def test_to_yaml_produces_valid_yaml(tiny_ir: ValidationIR) -> None:
    parsed = yaml.safe_load(tiny_ir.to_yaml())
    assert parsed["version"] == "1"
    assert parsed["datasets"][0]["name"] == "tiny"
