from typing import Any

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema


class BBox:
    """
    Immutable 2D bounding box primitive.

    This type is a geometric primitive with representations that can differ significantly between
    different data formats. Consequently, does not derive from the Pydantic `BaseModel` although it
    can participate in a `BaseModel` as a field.

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

    __slots__ = ("_xmin", "_ymin", "_xmax", "_ymax")

    _xmin: float | int
    _ymin: float | int
    _xmax: float | int
    _ymax: float | int

    def __init__(
        self, xmin: float | int, ymin: float | int, xmax: float | int, ymax: float | int
    ) -> None:
        if not isinstance(xmin, float | int):
            raise TypeError(
                f"`xmin` must be a `float` or `int`; but {repr(xmin)} is a `{type(xmin).__name__}`"
            )
        elif not isinstance(ymin, float | int):
            raise TypeError(
                f"`ymin` must be a `float` or `int`; but {repr(ymin)} is a `{type(ymin).__name__}`"
            )
        elif not isinstance(xmax, float | int):
            raise TypeError(
                f"`xmax` must be a `float` or `int`; but {repr(xmax)} is a `{type(xmax).__name__}`"
            )
        elif not isinstance(ymax, float | int):
            raise TypeError(
                f"`ymax` must be a `float` or `int`; but {repr(ymax)} is a `{type(ymax).__name__}`"
            )
        object.__setattr__(self, "_xmin", xmin)
        object.__setattr__(self, "_ymin", ymin)
        object.__setattr__(self, "_xmax", xmax)
        object.__setattr__(self, "_ymax", ymax)

    def __setattr__(self, _: str, __: object) -> None:
        raise AttributeError(f"`{self.__class__.__name__} is immutable")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, BBox)
            and self.xmin == other.xmin
            and self.ymin == other.ymin
            and self.xmax == other.xmax
            and self.ymax == other.ymax
        )

    def __hash__(self) -> int:
        return hash((self.xmin, self.ymin, self.xmax, self.ymax))

    def __repr__(self) -> str:
        return f"BBox({self.xmin}, {self.ymin}, {self.xmax}, {self.ymax})"

    def __str__(self) -> str:
        return f"({self.xmin}, {self.ymin}, {self.xmax}, {self.ymax})"

    @property
    def xmin(self) -> float | int:
        """
        float | int: Minimum X-coordinate
        """
        return self._xmin

    @property
    def ymin(self) -> float | int:
        """
        float | int: Minimum Y-coordinate
        """
        return self._ymin

    @property
    def xmax(self) -> float | int:
        """
        float | int: Maximum X-coordinate
        """
        return self._xmax

    @property
    def ymax(self) -> float | int:
        """
        float | int: Maximum Y-coordinate
        """
        return self._ymax

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
    def from_geo_json(
        cls, *bbox: float | int | tuple[float | int, ...] | list[float | int]
    ) -> "BBox":
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
                f"{repr(v)} (type `{t}` at index {i})"
                for (i, v, t) in incompatible_items
            )
            raise TypeError(
                f"`bbox` must contain only `float` or `int`; but {repr(bbox)} contains the following incompatible values: {incompatible_str} "
            )

        return BBox(bbox[0], bbox[1], bbox[2], bbox[3])

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: type[Any], _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validator(
            value: BBox | tuple[float | int, ...] | list[float | int],
            info: ValidationInfo,
        ) -> "BBox":
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
                            ctx={"error": f"invalid bounding box value: {str(e)}"},
                        )
                    ],
                ) from e

        def serialize_bbox(
            v: "BBox", info: ValidationInfo | None
        ) -> "tuple[float | int, ...] | 'BBox'":
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
            "type": "array",
            "minItems": 4,
            "maxItems": 4,  # Expressly limit to subset of GeoJSON bboxes that are 2D.
            "items": {
                "type": "number",
            },
        }
