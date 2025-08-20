from dataclasses import dataclass
from typing import Any

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema


@dataclass(order=True, frozen=True, slots=True)
class BBox:
    """
    Two-dimensional bounding box.

    Parameters
    ----------
    xmin : float | int
        Minimum X-coordinate
    ymin : float | int
        Minimum Y-coordiate
    xmax : float | int
        Maximum X-coordinate
    ymax : float | int
        Maximum Y-coordinate


    Attributes
    ----------
    xmin : float | int
        Minimum X-coordinate
    ymin : float | int
        Minimum Y-coordiate
    xmax : float | int
        Maximum X-coordinate
    ymax : float | int
        Maximum Y-coordinate


    Examples
    --------
    Create a bounding box:

    >>> bbox = BBox(xmin=-123.5, ymin=37.7, xmax=-122.4, ymax=38.0)

    Serialize a bounding box to its GeoJSON representation:

    >>> BBox(1, 2, 3, 4).to_geo_json()
    (1, 2, 3, 4)

    Read a bounding box from its GeoJSON representation:

    >>> BBox.from_geo_json([1, 2, 3, 4])
    BBox(xmin=1, ymin=2, xmax=3, ymax=4)

    Read a bounding box from its GeoJSON representation (simplified form for easier interactive use):

    >>> BBox.from_geo_json(1, 2, 3, 4)
    BBox(xmin=1, ymin=2, xmax=3, ymax=4)
    """

    xmin: float | int
    ymin: float | int
    xmax: float | int
    ymax: float | int

    def __post_init__(self) -> None:
        if not isinstance(self.xmin, float | int):
            raise TypeError(f"`xmin` must be a `float` or `int`; but {repr(self.xmin)} is a `{type(self.xmin).__name__}`")
        elif not isinstance(self.ymin, float | int):
            raise TypeError(f"`ymin` must be a `float` or `int`; but {repr(self.ymin)} is a `{type(self.ymin).__name__}`")
        elif not isinstance(self.xmax, float | int):
            raise TypeError(f"`xmax` must be a `float` or `int`; but {repr(self.xmax)} is a `{type(self.xmax).__name__}`")
        elif not isinstance(self.ymax, float | int):
            raise TypeError(f"`ymax` must be a `float` or `int`; but {repr(self.ymax)} is a `{type(self.ymax).__name__}`")

    def to_geo_json(self) -> tuple[float | int, ...]:
        """
        Return a GeoJSON-compliant `bbox` array.

        Returns
        -------
        tuple of float
            GeoJSON-compliant bounding box coordinates array.
        """
        return (self.xmin, self.ymin, self.xmax, self.ymax)

    @classmethod
    def from_geo_json(cls, *bbox: float | int | tuple[float | int, ...] | list[float | int]) -> "BBox":
        """
        Convert a GeoJSON-compliant `bbox` array into a `Bbox` value.

        Parameters
        ----------
        bbox : tuple[float | int, ...] | list[float | int]
            GeoJSON-compliant `bbox` array containing 4 numbers

        Returns
        -------
        BBox
            `BBox` instance corresponding to the input `bbox` array

        Raises
        ------
        TypeError
            If `bbox` is not a `tuple` or `list` or contains non-numeric values
        ValueError
            If `bbox` is a `tuple` or `list` and does not have length 4
        """
        if len(bbox) == 1 and isinstance(bbox[0], tuple | list):
            return cls._from_geo_json(bbox[0])
        else:
            return cls._from_geo_json(bbox)

    @classmethod
    def _from_geo_json(cls, bbox: tuple | list) -> "BBox":
        n: int = len(bbox)

        if not isinstance(bbox, tuple | list):
            raise TypeError(
                f"`bbox` must be a `tuple` or `list`; but {repr(bbox)} is a `{type(bbox).__name__}`"
            )
        elif n != 4:
            raise ValueError(
                f"`bbox` must have length 4; but {repr(bbox)} has length {n}"
            )

        incompatible_items = [
            (i, v, type(v).__name__)
            for i, v in enumerate(bbox)
            if not isinstance(v, float | int)
        ]
        if len(incompatible_items) > 0:
            incompatible_str = ",".join(
                f"{repr(v)} (type `{t}` at index {i})" for (i, v, t) in incompatible_items
            )
            raise TypeError(
                f"`bbox` must contain only `float` or `int`; but {repr(bbox)} contains the following incompatible values: {incompatible_str} "
            )

        return BBox(bbox[0], bbox[1], bbox[2], bbox[3])


    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: type[Any], _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validator(value: BBox | tuple[float | int, ...] | list[float | int], info: ValidationInfo) -> "BBox":
            try:
                if isinstance(value, BBox):
                    return value
                elif isinstance(value, tuple | list):
                    return cls.from_geo_json(value)
                elif isinstance(value, dict):
                    BBox(**value)
                else:
                    raise TypeError(
                        f"expected `BBox` or `tuple` or `list`; got `{type(value).__name__}` with value {repr(value)}"
                    )
            except Exception as e:
                context = info.context or {}
                loc = context.get("loc_prefix", ()) + ("value",)
                raise ValidationError.from_exception_data(
                    title=cls.__name__,
                    line_errors=[
                        InitErrorDetails(
                            type="value_error",
                            loc=loc,
                            input=value,
                            ctx={"error": f"invalid bounding box value: {str(e)}"}
                        )
                    ]
                ) from e

        def serialize_bbox(v: "BBox", info: ValidationInfo | None) -> "tuple[float | int, ...] | 'BBox'":
            if info and info.mode == "json":
                return v.to_geo_json()
            return v

        return core_schema.with_info_plain_validator_function(
            validator,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize_bbox, info_arg=True
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        return {
            'type': 'array',
            'minItems': 4,
            'maxItems': 4,  # Expressly limit to subset of GeoJSON bboxes that are 2D.
            'items': {
                'type': 'number',
            }
        }
