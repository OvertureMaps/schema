"""Cartography-related models for Overture Maps features."""

from pydantic import Field

from overture.schema.core.base import StrictBaseModel


class CartographyContainer(StrictBaseModel):
    """Cartographic hints for optimal map display."""

    # Optional

    prominence: int | None = Field(
        default=None, ge=1, le=100, description="Feature significance/importance"
    )
    min_zoom: int | None = Field(
        default=None, ge=0, le=23, description="Minimum recommended zoom level"
    )
    max_zoom: int | None = Field(
        default=None, ge=0, le=23, description="Maximum recommended zoom level"
    )
    sort_key: int = Field(default=0, description="Drawing order (lower = on top)")
