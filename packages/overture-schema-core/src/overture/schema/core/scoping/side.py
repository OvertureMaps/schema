"""
Types supporting the side scope.
"""

from overture.schema.system.doc import DocumentedEnum


class Side(str, DocumentedEnum):
    """
    The side, left or right, on which something appears relative to a facing or heading direction
    (*e.g.*, the side of a road relative to the road orientation), or relative to the direction of
    travel of a person or vehicle.
    """

    LEFT = ("left", "On the left relative to the facing direction")
    RIGHT = ("right", "On the right side relative to the facing direction")
