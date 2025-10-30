import textwrap
from datetime import datetime
from typing import Annotated, NewType

from pydantic import BaseModel, Field

from overture.schema.core.scoping import Scope, scoped
from overture.schema.core.types import ConfidenceScore
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.string import JsonPointer, StrippedString


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class SourceItem(BaseModel):
    """
    Specifies the source of the data used for a feature or one of its properties.
    """

    # Required

    property: JsonPointer = Field(
        description=textwrap.dedent("""
            A JSON Pointer identifying the property (field) that this source information applies to.

            The root document value `""` indicates that this source information applies to the
            entire feature, excepting properties (fields) for which a dedicated source information
            record exists.

            Any other JSON Pointer apart from `""` indicates that this source record provides
            dedicated source information for the property at the path in the JSON Pointer. As an
            example, the value `"/names/common/en"` indicates that the source information applies to
            the English common name of a named feature, while the value `"/geometry"` indicates that
            it applies to the feature geometry.
        """).strip()
    )
    dataset: str = Field(
        description=textwrap.dedent("""
            Name of the dataset where the source data can be found.
        """).strip()
    )

    # Optional

    license: Annotated[
        StrippedString | None,
        Field(
            description=textwrap.dedent("""
                Source data license name.

                This should be a valid SPDX license identifier when available.

                If omitted, contact the data provider for more license information.
            """).strip()
        ),
    ] = None
    record_id: Annotated[
        str | None,
        Field(
            description=textwrap.dedent(
                """
                Identifies the specific record within the source dataset where the source data can
                be found.

                The format of record identifiers is dataset-specific.
            """
            ).strip()
        ),
    ] = None
    update_time: Annotated[
        datetime | None,
        Field(description="Last update time of the source data record."),
    ] = None
    confidence: Annotated[
        ConfidenceScore | None,
        Field(
            description=textwrap.dedent("""
                Confidence value from the source dataset.

                This is a value between 0.0 and 1.0 and is particularly relevant for ML-derived data.
            """).strip()
        ),
    ] = None


Sources = NewType(
    "Sources",
    Annotated[
        list[SourceItem],
        Field(
            min_length=1,
            description="""Information about the source data used to assemble the feature.""",
        ),
        UniqueItemsConstraint(),
    ],
)
