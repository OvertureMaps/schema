"""Hand-written Spark StructType fragments for types the codegen can't generate.

The codegen builds feature schemas by walking Pydantic `BaseModel`
subclasses. `BBox` is a plain class, not a `BaseModel`, so extraction
can't reach it -- `BBOX_STRUCT` is hand-written here to fill the gap.
Every other nested type is a `BaseModel` and gets generated directly
into each feature module, which is why this file holds only the one
struct.
"""

from __future__ import annotations

from pyspark.sql.types import DoubleType, StructField, StructType

BBOX_STRUCT = StructType(
    [
        StructField("xmin", DoubleType(), True),
        StructField("xmax", DoubleType(), True),
        StructField("ymin", DoubleType(), True),
        StructField("ymax", DoubleType(), True),
    ]
)
