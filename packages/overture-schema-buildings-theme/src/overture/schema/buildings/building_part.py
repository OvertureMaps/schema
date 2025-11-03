"""
The `BuildingPart` feature type model and supporting types.
"""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.buildings._common import Appearance
from overture.schema.buildings.building import Building
from overture.schema.core import OvertureFeature
from overture.schema.core.models import Stacked
from overture.schema.core.names import Named
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.ref import Id, Reference, Relationship


class BuildingPart(
    OvertureFeature[Literal["buildings"], Literal["building_part"]],
    Named,
    Stacked,
    Appearance,
):
    """
    Building parts represent parts of larger building features. They allow buildings to be modeled
    in rich detail suitable for creating realistic 3D models.

    Every building part is associated with a parent `Building` feature via the `building_id` field.
    In addition, a building part has a footprint geometry and may include additional details such as
    its height, the number of floors, and the color and material of its facade and roof.

    Building parts can float or be stacked on top of each other. The `min_height`, `min_floor`,
    `height`, and `num_floors`, fields can be used to arrange the parts correctly along the
    vertical dimension.
    """

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="The footprint or roofprint of the building part.",
        ),
    ]

    # Required

    building_id: Annotated[
        Id,
        Field(description="The building to which this part belongs"),
        Reference(Relationship.BELONGS_TO, Building),
    ]
