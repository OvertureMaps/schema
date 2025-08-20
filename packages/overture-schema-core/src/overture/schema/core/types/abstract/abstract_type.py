from dataclasses import dataclass, field
from typing import Annotated, Any

from pydantic import Field
from pydantic.fields import FieldInfo


@dataclass(frozen=True)
class AbstractTypeDefinition:
    """Type-safe definition for an abstract data type."""

    base: type[Any]
    constraints: FieldInfo | None = None
    target_mappings: dict[str, str] = field(default_factory=dict)
    json_schema_override: dict[str, Any] | None = None


class AbstractTypeRegistry:
    """Internal registry of abstract type definitions."""

    TYPES = {
        "UINT8": AbstractTypeDefinition(
            base=int,
            constraints=Field(ge=0, le=255),
            target_mappings={
                "scala": "Byte",  # Note: Scala Byte is signed, but closest match
                "spark": "ByteType",
                "parquet": "INT32",  # Parquet promotes small ints
            },
        ),
        "UINT16": AbstractTypeDefinition(
            base=int,
            constraints=Field(ge=0, le=65535),
            target_mappings={
                "scala": "Short",  # Note: Scala Short is signed
                "spark": "ShortType",
                "parquet": "INT32",
            },
        ),
        "UINT32": AbstractTypeDefinition(
            base=int,
            constraints=Field(ge=0, le=4294967295),
            target_mappings={
                "scala": "Long",  # Use Long for safety since Int is signed
                "spark": "LongType",
                "parquet": "INT64",  # Promote to avoid overflow
            },
        ),
        "INT8": AbstractTypeDefinition(
            base=int,
            constraints=Field(ge=-128, le=127),
            target_mappings={
                "scala": "Byte",
                "spark": "ByteType",
                "parquet": "INT32",
            },
        ),
        "INT32": AbstractTypeDefinition(
            base=int,
            constraints=Field(ge=-(2**31), le=2**31 - 1),
            target_mappings={
                "scala": "Int",
                "spark": "IntegerType",
                "parquet": "INT32",
            },
        ),
        "INT64": AbstractTypeDefinition(
            base=int,
            constraints=Field(ge=-(2**63), le=2**63 - 1),
            target_mappings={
                "scala": "Long",
                "spark": "LongType",
                "parquet": "INT64",
            },
        ),
        "FLOAT32": AbstractTypeDefinition(
            base=float,
            target_mappings={
                "scala": "Float",
                "spark": "FloatType",
                "parquet": "FLOAT",
            },
            json_schema_override={"type": "number"},
        ),
        "FLOAT64": AbstractTypeDefinition(
            base=float,
            target_mappings={
                "scala": "Double",
                "spark": "DoubleType",
                "parquet": "DOUBLE",
            },
            json_schema_override={"type": "number"},
        ),
        "GEOMETRY": AbstractTypeDefinition(
            base=object,  # Generic base for geometry
            target_mappings={
                "scala": "org.locationtech.jts.geom.Geometry",
                "spark": "GeometryType",
                "parquet": "BYTE_ARRAY",  # WKB
                "json": "custom",  # TODO GeoJSON
            },
        ),
    }


class AbstractType:
    """Clean type dispatcher for creating annotated types."""

    @classmethod
    def __class_getitem__(cls, type_name: str) -> Any:  # noqa: ANN401
        """Create an Annotated type for the given abstract type name."""
        if type_name not in AbstractTypeRegistry.TYPES:
            raise ValueError(f"Unknown abstract type: {type_name}")

        type_def = AbstractTypeRegistry.TYPES[type_name]

        # Build metadata list - include type definition for introspection
        metadata: list[Any] = [type_def]

        # Add constraints if they exist
        if type_def.constraints:
            metadata.append(type_def.constraints)

        return Annotated[(type_def.base, *metadata)]
