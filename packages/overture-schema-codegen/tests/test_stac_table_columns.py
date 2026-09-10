"""Tests for the STAC `table:columns` renderer.

A Column Object is `name`, `type`, `description`, so most of what this renderer
knows it cannot say. These cover the decisions that survive that flattening: how
an absent description is rendered, what happens at a union collision, and the two
cases where guessing is worse than refusing.
"""

import json
from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field

from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.stac_table_columns.exceptions import (
    TableColumnsUnrepresentable,
)
from overture.schema.codegen.stac_table_columns.pipeline import (
    generate_table_columns_documents,
)
from overture.schema.codegen.stac_table_columns.renderer import (
    VECTOR_EXTENSION_URI,
    render_table_columns,
)
from overture.schema.system.geometric import (
    BBox,
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.numeric import float32, float64, int32, int64


def _capabilities(doc: object) -> set[str]:
    return {g.capability for g in doc.gaps}  # type: ignore[attr-defined]


def _columns(model: type[BaseModel]) -> dict[str, dict[str, object]]:
    doc = render_table_columns(extract_model(model))
    return {c["name"]: c for c in doc.stac_fields()["table:columns"]}


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


def test_scalar_columns_use_arrow_names() -> None:
    """`type` uses Arrow's names, the ones a reader of the released GeoParquet
    reports -- `double` and `float`, not `float64`/`float32`, and `string`,
    `bool`, `binary` rather than DuckDB's `varchar`, `boolean`, `blob`. Every
    name here came from `pyarrow`'s own stringifier."""

    class M(BaseModel):
        big: float64
        small: float32
        label: str
        flag: bool
        raw: bytes
        count: int64

    columns = _columns(M)

    assert columns["big"]["type"] == "double"
    assert columns["small"]["type"] == "float"
    assert columns["label"]["type"] == "string"
    assert columns["flag"]["type"] == "bool"
    assert columns["raw"]["type"] == "binary"
    assert columns["count"]["type"] == "int64"


def test_composite_columns_use_arrow_angle_bracket_grammar() -> None:
    """Structs, lists and maps are the part most likely to drift.

    DuckDB wrote these `struct(name type, ...)`, `type[]` and
    `map(varchar, varchar)`; Arrow uses angle brackets and names a
    list's child `item`. Pinning the whole nested string is the point -- a
    per-scalar check would pass against either grammar.
    """

    class Inner(BaseModel):
        depth: float64
        tag: str

    class M(BaseModel):
        nested: Inner
        labels: list[str]
        matrix: list[list[int32]]
        lookup: dict[str, str]

    columns = _columns(M)

    assert columns["nested"]["type"] == "struct<depth: double, tag: string>"
    assert columns["labels"]["type"] == "list<item: string>"
    assert columns["matrix"]["type"] == "list<item: list<item: int32>>"
    assert columns["lookup"]["type"] == "map<string, string>"


def test_geometry_is_binary_and_the_erasure_is_logged() -> None:
    """Arrow has no geometry type; GeoParquet stores WKB in a binary column.

    `binary` is what an Arrow reader reports for Overture's own released
    geometry column, so it is what this renderer emits. The semantic the
    DuckDB name carried in the type string is gone, and the gap log is
    what records that -- `vector:geometry_types` carries only the part the
    schema can assert.
    """

    class M(BaseModel):
        geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.POINT)]

    doc = render_table_columns(extract_model(M))
    columns = {c["name"]: c for c in doc.stac_fields()["table:columns"]}

    assert columns["geometry"]["type"] == "binary"
    assert columns["geometry"]["vector:geometry_types"] == ["Point"]
    assert any(g.kind == "target-dialect" and "geometry" in g.detail for g in doc.gaps)


def test_type_and_data_type_differ_for_floats_on_purpose() -> None:
    """The two fields speak different vocabularies, and neither is bent.

    `data_type` is bound to STAC common metadata, which names floats
    `float32`/`float64`; `type` is bound to Arrow, which names the same two
    `float`/`double`.
    """

    class M(BaseModel):
        small: float32
        big: float64

    columns = _columns(M)

    assert columns["small"]["type"] == "float"
    assert columns["small"]["data_type"] == "float32"
    assert columns["big"]["type"] == "double"
    assert columns["big"]["data_type"] == "float64"


def test_bbox_struct_members_follow_the_model_not_a_publisher() -> None:
    """The bbox struct's member order is the `BBox` class's declaration order.

    It does not match the order Overture ships (`xmin, xmax, ymin, ymax`, what
    the PySpark `BBOX_STRUCT` declares). That discrepancy is accepted: this
    renderer derives types from models, and matching one publisher's file
    layout would encode a fact about that publisher rather than the schema.
    """

    class M(BaseModel):
        bbox: BBox

    assert (
        _columns(M)["bbox"]["type"]
        == "struct<xmin: double, ymin: double, xmax: double, ymax: double>"
    )


def test_data_type_maps_a_numeric_column_to_the_stac_vocabulary() -> None:
    """A numeric base type resolves to STAC common metadata's own name.

    Overture's `int32`/`float64` names already ARE the vocabulary's names, so
    this is a pass-through, not a translation.
    """

    class M(BaseModel):
        count: int32
        ratio: float64

    doc = render_table_columns(extract_model(M))
    columns = {c["name"]: c for c in doc.stac_fields()["table:columns"]}

    assert columns["count"]["data_type"] == "int32"
    assert columns["ratio"]["data_type"] == "float64"


def test_data_type_falls_back_to_other_for_a_non_numeric_column() -> None:
    """A string, a struct, and everything else with no numeric identity get
    `other` -- a member of the STAC vocabulary, not an omission."""

    class Nested(BaseModel):
        value: str

    class M(BaseModel):
        label: str
        nested: Nested

    doc = render_table_columns(extract_model(M))
    columns = {c["name"]: c for c in doc.stac_fields()["table:columns"]}

    assert columns["label"]["data_type"] == "other"
    assert columns["nested"]["data_type"] == "other"


def test_geometry_type_constraint_becomes_vector_geometry_types() -> None:
    """A single allowed geometry type becomes a one-element `vector:geometry_types`.

    v1.3.0's README defines no `geometry_type` on the Column Object at all,
    only `vector:geometry_types` from the separate Vector extension (see the
    renderer module docstring).
    """

    class M(BaseModel):
        geometry: Annotated[
            Geometry,
            GeometryTypeConstraint(GeometryType.POINT),
            Field(description="the shape"),
        ]

    doc = render_table_columns(extract_model(M))
    columns = {c["name"]: c for c in doc.stac_fields()["table:columns"]}

    assert columns["geometry"]["vector:geometry_types"] == ["Point"]


def test_multiple_allowed_geometry_types_are_sorted_geojson_names() -> None:
    """Several allowed types become a sorted list of GeoJSON (not snake_case) names."""

    class M(BaseModel):
        geometry: Annotated[
            Geometry,
            GeometryTypeConstraint(GeometryType.MULTI_POLYGON, GeometryType.POLYGON),
        ]

    doc = render_table_columns(extract_model(M))
    columns = {c["name"]: c for c in doc.stac_fields()["table:columns"]}

    assert columns["geometry"]["vector:geometry_types"] == ["MultiPolygon", "Polygon"]


def test_unconstrained_geometry_omits_vector_geometry_types_and_logs_a_gap() -> None:
    """No `GeometryTypeConstraint` means no claim about which types can appear.

    Emitting all seven would assert something the schema never said; omitting
    silently would look identical to forgetting the field. The gap log is the
    only record.
    """

    class M(BaseModel):
        geometry: Geometry

    doc = render_table_columns(extract_model(M))
    columns = {c["name"]: c for c in doc.stac_fields()["table:columns"]}

    assert "vector:geometry_types" not in columns["geometry"]
    assert any(
        g.kind == "ir-gap" and g.capability == "geometry types" for g in doc.gaps
    )


def test_pipeline_declares_the_vector_extension_only_when_used() -> None:
    """`stac_extensions` gains the Vector extension exactly when a column needs it.

    A `vector:` field with its extension undeclared would not validate; a
    model with no geometry constraint should not carry a URI for a field it
    never emits.
    """

    class Constrained(BaseModel):
        geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.POINT)]

    class Unconstrained(BaseModel):
        geometry: Geometry

    [with_vector] = generate_table_columns_documents([extract_model(Constrained)])
    [without_vector] = generate_table_columns_documents([extract_model(Unconstrained)])

    assert VECTOR_EXTENSION_URI in json.loads(with_vector.stac)["stac_extensions"]
    assert (
        VECTOR_EXTENSION_URI not in json.loads(without_vector.stac)["stac_extensions"]
    )


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
