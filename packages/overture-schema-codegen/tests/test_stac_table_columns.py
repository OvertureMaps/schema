"""Tests for the STAC `table:columns` renderer.

A Column Object is `name`, `type`, `description`, so most of what this renderer
knows it cannot say. These cover the decisions that survive that flattening: how
an absent description is spelled, what happens at a union collision, and the two
cases where guessing is worse than refusing.
"""

from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field

from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.stac_table_columns.exceptions import (
    TableColumnsUnrepresentable,
)
from overture.schema.codegen.stac_table_columns.renderer import render_table_columns
from overture.schema.system.geometric import Geometry


def _capabilities(doc: object) -> set[str]:
    return {g.capability for g in doc.gaps}  # type: ignore[attr-defined]


def test_undescribed_column_omits_the_key_entirely() -> None:
    """A column with no description omits `description`, never emits `""`.

    The two are not interchangeable downstream: an omitted key leaves the
    undescribed set as something a consumer can query for, while an empty string
    is a description that happens to say nothing, and no count can tell it from
    one that was authored badly.
    """

    class M(BaseModel):
        described: Annotated[str, Field(description="what it is")]
        bare: str

    doc = render_table_columns(extract_model(M))
    columns = {c["name"]: c for c in doc.stac_fields()["table:columns"]}

    assert columns["described"]["description"] == "what it is"
    assert "description" not in columns["bare"]


def test_primary_geometry_is_emitted_when_exactly_one_geometry_exists() -> None:
    """One geometry column resolves `table:primary_geometry` unambiguously."""

    class M(BaseModel):
        geometry: Annotated[Geometry, Field(description="the shape")]
        name: str

    doc = render_table_columns(extract_model(M))

    assert doc.stac_fields()["table:primary_geometry"] == "geometry"


def test_two_geometries_omit_primary_rather_than_guessing() -> None:
    """Nothing in the IR says which of two geometry columns is primary.

    Picking the first would invent a fact about the data, so the key is omitted
    and the ambiguity is logged as an IR gap. This is the direction that
    discriminates: the shipped models all carry exactly one geometry column, so
    without a synthetic pair the branch is never exercised.
    """

    class M(BaseModel):
        footprint: Annotated[Geometry, Field(description="one")]
        centroid: Annotated[Geometry, Field(description="another")]

    doc = render_table_columns(extract_model(M))

    assert "table:primary_geometry" not in doc.stac_fields()
    assert any(
        g.kind == "ir-gap" and g.capability == "primary geometry" for g in doc.gaps
    )


def test_row_count_is_never_emitted() -> None:
    """`table:row_count` is a property of data; this path has only a schema.

    Emitting a placeholder would be a fabricated measurement, so the key is
    absent by construction rather than by omission.
    """

    class M(BaseModel):
        id: str

    assert "table:row_count" not in render_table_columns(extract_model(M)).stac_fields()


def test_union_name_collision_is_logged_not_silently_dropped() -> None:
    """Two arms contributing one column name emit a `flatten-collision`.

    Both arms stringify to the same physical type, so nothing downstream can
    refuse the merge and nothing else records that an arm's meaning was lost.
    This gap is the only trace.
    """

    class Base(BaseModel):
        pass

    class Left(Base):
        kind: Literal["left"]
        value: Annotated[str, Field(description="a left value")]

    class Right(Base):
        kind: Literal["right"]
        value: Annotated[str, Field(description="a right value")]

    class Holder(BaseModel):
        item: Annotated[Left | Right, Field(discriminator="kind")]

    doc = render_table_columns(extract_model(Holder))

    assert any(g.kind == "flatten-collision" for g in doc.gaps)


def test_optionality_is_reported_as_lost_for_every_column() -> None:
    """A Column Object has no required, nullable or optional keyword.

    Unlike a constraint, this one cannot be expressed at all, so it is logged
    for every column rather than only for the ones that declare something.
    """

    class M(BaseModel):
        required: str
        optional: str | None = None

    doc = render_table_columns(extract_model(M))

    assert "optionality" in _capabilities(doc)


def test_strict_mode_raises_rather_than_returning_a_gap_log() -> None:
    """`strict=True` turns the log into a refusal.

    The default is to emit and report, because a flattening target that refused
    on every loss would never emit at all; strict is for a caller that wants the
    losses to be fatal.
    """

    class M(BaseModel):
        anything: str | None = None

    with pytest.raises(TableColumnsUnrepresentable):
        render_table_columns(extract_model(M), strict=True)


def test_gap_log_is_non_empty_for_a_real_model() -> None:
    """The did-happen control for every assertion above.

    Each test that asserts a *particular* capability was logged would pass just
    as well against a renderer whose log was accidentally empty of everything
    else. This one fails if the log stops being populated at all.
    """

    class M(BaseModel):
        bounded: Annotated[int, Field(ge=0, le=10)]

    doc = render_table_columns(extract_model(M))

    assert doc.gaps
    assert "constraint" in _capabilities(doc)
