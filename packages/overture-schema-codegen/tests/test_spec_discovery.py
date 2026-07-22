"""Tests for `extract_model_spec`, the discovery-to-spec bridge."""

import logging

import pytest
from codegen_test_support import TollChargesByVehicleType
from overture.schema.codegen.spec_discovery import extract_model_spec
from overture.schema.system.discovery import ModelKey


def test_rootmodel_entry_point_is_skipped_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A discovered RootModel entry point is skipped, not generated.

    Entry points contribute custom classes, not only top-level tables: an
    extension may register a RootModel as a type used as a field elsewhere.
    A RootModel has no record structure of its own -- it serializes as its
    bare root value -- so it drops out of generation. The skip is warned,
    not raised: it is a legitimate contribution rather than a mistake, and
    a silent drop would leave a registered entry point missing with no
    signal.
    """
    key = ModelKey(
        name="toll_charges",
        entry_point="codegen_test_support:TollChargesByVehicleType",
        tags=frozenset(),
    )
    with caplog.at_level(logging.WARNING):
        result = extract_model_spec(key, TollChargesByVehicleType)

    assert result is None
    assert "RootModel" in caplog.text
    assert "toll_charges" in caplog.text
