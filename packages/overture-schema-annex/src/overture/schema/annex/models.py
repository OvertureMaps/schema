"""Sources schema models for Overture Maps data sources."""

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, HttpUrl

from overture.schema.core.models import StrictBaseModel
from overture.schema.core.types import CountryCodeAlpha2

from .enums import BuildSource, UpdateType
from .types import LicenseShortname


class Dataset(StrictBaseModel):
    """Dataset definition for Overture Maps data sources."""

    # Required

    source_name: Annotated[
        str,
        Field(description="The name of the source."),
    ]
    source_dataset_name: Annotated[
        str,
        Field(
            description="The name of the dataset being used from the source. This should match the 'dataset' value found in a record's sources column."
        ),
    ]
    data_url: Annotated[
        HttpUrl | Literal[""],
        Field(
            description="The data page or data portal of this source, typically includes links to data downloads and license links.",
        ),
    ]
    data_url_archived: Annotated[
        HttpUrl | Literal[""],
        Field(
            description="URL of the source's data page, stored on archive.org, at or near the date the source data was obtained for use within Overture.",
        ),
    ]
    license_url: Annotated[
        HttpUrl | Literal[""],
        Field(
            description="A link to this source's data license or page referencing the license associated with the data being imported. This should include explicit license terms.",
        ),
    ]
    license_url_archived: Annotated[
        HttpUrl | Literal[""],
        Field(
            description="URL of the source's license page, stored on archive.org, at or near the date the source data was obtained for use within Overture.",
        ),
    ]
    license_type: Annotated[
        str,
        Field(
            description="The license that is associated with the data being used from this source. This should be a valid SPDX license identifier when available."
        ),
    ]
    license_text: Annotated[
        str,
        Field(
            description="Any relevant license text, direct from the source's license page."
        ),
    ]
    license_attribution: Annotated[
        str,
        Field(description="Any attribution required by this source."),
    ]
    coverage_bbox: Annotated[
        list[float],
        Field(
            description="The bounding box, in [xmin, ymin, xmax, ymax] format, of this source's coverage.",
            min_length=4,
            max_length=4,
        ),
    ]

    # Optional

    inception_date: Annotated[
        date | None,
        Field(
            description="The first date this source was used in the Overture addresses theme, in YYYY-MM-DD format."
        ),
    ] = None
    url: Annotated[
        HttpUrl | None,
        Field(description="The home page of this source."),
    ] = None
    url_archived: Annotated[
        HttpUrl | None,
        Field(
            description="URL of the source's home page, stored on archive.org, at or near the date the source data was obtained for use within Overture.",
        ),
    ] = None
    data_download_url: Annotated[
        list[HttpUrl | Literal[""]] | None,
        Field(
            description="Either a direct download link of data from this source, typically a geo-format or compressed file, or an endpoint from where the data was obtained for use within Overture."
        ),
    ] = None
    countries: Annotated[
        list[CountryCodeAlpha2 | Literal["Global"]] | None,
        Field(
            description="A list of two-character iso country codes that this data source provides data in."
        ),
    ] = None
    coverage_description: Annotated[
        str | None,
        Field(
            description="A description of the coverage type of the source data - i.e. national, regional, local."
        ),
    ] = None
    data_layer_name: Annotated[
        str | None,
        Field(description="Name of the data layer used from this source."),
    ] = None
    oa_path: Annotated[
        list[str] | None,
        Field(description="File path and name in OpenAddresses, if existing."),
    ] = None
    address_levels: Annotated[
        list[str] | None,
        Field(
            description="Available address level attributes from OpenAddress, if existing."
        ),
    ] = None
    file_format: Annotated[
        str | None,
        Field(description="Format of the file used from this source."),
    ] = None
    update_frequency: Annotated[
        str | None,
        Field(description="How frequently the source data is updated upstream."),
    ] = None
    build_source: BuildSource | None = None
    update_type: UpdateType | None = None
    update_schedule: Annotated[
        list[str] | None,
        Field(
            description="The month or months in which the data is to be re-ingested by the Overture theme using this data source."
        ),
    ] = None
    known_issues: Annotated[
        str | None,
        Field(
            description="A description of any issues with the data that are known - i.e. data is incomplete, coverage is incomplete, or issues with character encoding."
        ),
    ] = None
    notes: Annotated[
        str | None,
        Field(
            description="Freeform notes about this data source, including notes on any pre-processing requirements."
        ),
    ] = None
    requires_attribution: Annotated[
        str | None,  # TODO should this be a bool?
        Field(
            description="Whether this source requires attribution to be used in Overture Maps."
        ),
    ] = None


class Sources(StrictBaseModel):
    """Common schema definitions for data sources."""

    # Required

    datasets: Annotated[
        list[Dataset],
        Field(description="List of data source entries used by Overture."),
    ]
    license_priority: Annotated[
        dict[LicenseShortname, Annotated[int, Field(ge=0)]],
        Field(
            description="Map of license shortnames to their priority (lower number indicates higher priority)."
        ),
        Field(json_schema_extra={"additionalProperties": False}),
    ]
