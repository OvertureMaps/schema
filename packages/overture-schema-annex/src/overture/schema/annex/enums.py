from enum import Enum


class BuildSource(str, Enum):
    """The ingest source for address data."""

    OPEN_ADDRESSES = "OpenAddresses"
    TF_DATA_PLATFORM = "tf-data-platform"


class UpdateType(str, Enum):
    """Whether the data is continuously updated upstream or needs manual intervention."""

    CONTINUOUS = "continuous"
    MANUAL = "manual"
