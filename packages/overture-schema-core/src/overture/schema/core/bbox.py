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
class Dim:
    """
    Range of values representing a bounding box dimension.

    Parameters
    ----------
    min: float | int
        Minimum value of the bounding box dimension
    max: float | int
        Maximum value of the bounding box dimension

    Attributes
    ----------
    min: float | int
        Minimum value of the bounding box dimension
    max: float | int
        Maximum value of the bounding box dimension

    """

    min: float | int
    max: float | int

    def __post_init__(self) -> None:
        if not isinstance(self.min, float | int):
            raise TypeError(f"`min` must be a `float` or `int`; but {repr(self.min)} is a `{type(self.min).__name__}`")
        elif not isinstance(self.max, float | int):
            raise TypeError(f"`max` must be a `float` or `int`; but {repr(self.max)} is a `{type(self.max).__name__}`")



@dataclass(order=True, frozen=True, slots=True)
class BBox:
    """
    Bounding box with two or more dimensions.

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
    more : tuple[Dim, ...]
        Any additional dimensions after the first two


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
    more : tuple[Dim, ...]
        Any additional dimensions after the first two

    Examples
    --------
    Create a 2D bounding box:

    >>> bbox = BBox(xmin=-123.5, ymin=37.7, xmax=-122.4, ymax=38.0)

    Create a 3D bounding box:

    >>>  bbox = BBox(xmin=0, ymin=0, xmax=1, ymax=1, more=(Dim(0, 1))

    Create a 4D bounding box:

    >>>  bbox = BBox(xmin=0, ymin=0, xmax=1, ymax=1, more=(Dim(0, 1), Dim(-1, 0))
    """

    xmin: float | int
    ymin: float | int
    xmax: float | int
    ymax: float | int
    more: tuple[Dim, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.xmin, float | int):
            raise TypeError(f"`xmin` must be a `float` or `int`; but {repr(self.xmin)} is a `{type(self.xmin).__name__}`")
        elif not isinstance(self.ymin, float | int):
            raise TypeError(f"`ymin` must be a `float` or `int`; but {repr(self.ymin)} is a `{type(self.ymin).__name__}`")
        elif not isinstance(self.xmax, float | int):
            raise TypeError(f"`xmax` must be a `float` or `int`; but {repr(self.xmax)} is a `{type(self.xmax).__name__}`")
        elif not isinstance(self.ymax, float | int):
            raise TypeError(f"`ymax` must be a `float` or `int`; but {repr(self.ymax)} is a `{type(self.ymax).__name__}`")
        elif not isinstance(self.more, tuple | int):
            raise TypeError(f"`more` must be a `tuple`; but {repr(self.more)} is a `{type(self.more).__name__}`")

        bad_more_items = tuple((v, type(v).__name__) for v in self.more if not isinstance(v, Dim))
        if len(bad_more_items) > 0:
            bad_more_str = ",".join(
                f"{repr(v)} (type {t})" for (v, t) in bad_more_items
            )
            raise TypeError(f"`more` must contain only `Dim` values; but {self.more} contains the following non-`Dim` values: {bad_more_str}")

    def to_geo_json(self) -> tuple[float | int, ...]:
        """
        Return a GeoJSON-compliant `bbox` array.

        Returns
        -------
        tuple of float
            GeoJSON-compliant bounding box coordinates array.
        """
        return (self.xmin, self.ymin, *(dim.min for dim in self.more), self.xmax, self.ymax, *(dim.max for dim in self.more))

    @classmethod
    def from_geo_json(cls, bbox: tuple[float | int, ...] | list[float | int]) -> "BBox":
        """
        Convert a GeoJSON-compliant `bbox` array into a `Bbox` value.

        Parameters
        ----------
        bbox : tuple[float | int] | list[float | int]
            GeoJSON-compliant `bbox` array containing 2*n numbers for some n > 2, i.e. the length
            must be 4, 6, 8, ...

        Returns
        -------
        Bbox
            `Bbox` instance corresponding to the input `bbox` array

        Raises
        ------
        TypeError
            If `bbox` is not a `tuple` or `list` or contains non-numeric values
        ValueError
            If `bbox` does not have an even length at least 4
        """
        n: int = len(bbox)

        if not isinstance(bbox, tuple | list):
            raise TypeError(
                f"`bbox` must be a `tuple` or `list`; but {repr(bbox)} is a `{type(bbox).__name__}`"
            )
        elif n < 4:
            raise ValueError(
                f"`bbox` must have length at least 4; but {repr(bbox)} has length only {n}"
            )
        elif n % 2 != 0:
            raise ValueError(
                f"`bbox` length must be a multiple of 2; but {repr(bbox)} has length {n}"
            )

        incompatible_items = [
            (v, type(v).__name__)
            for v in bbox
            if not isinstance(v, float | int)
        ]
        if len(incompatible_items) > 0:
            incompatible_str = ",".join(
                f"{repr(v)} (type {t})" for (v, t) in incompatible_items
            )
            raise TypeError(
                f"`bbox` must contain only `float` or `int`; but {repr(bbox)} contains the following incompatible values:{incompatible_str} "
            )

        mid: int = int(n/2)
        more = tuple(Dim(min, max) for (min, max) in zip(bbox[2:mid], bbox[mid+2:], strict=False))

        return BBox(bbox[0], bbox[1], bbox[mid], bbox[mid+1], more) # type: ignore[misc]

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
            'items': {
                'type': 'number',
            }
        }
