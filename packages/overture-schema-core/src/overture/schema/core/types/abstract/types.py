from typing import Any, NewType

from overture.schema.core.geometry import Geometry

from .abstract_type import AbstractType, AbstractTypeDefinition, AbstractTypeRegistry

UInt8 = NewType("UInt8", AbstractType["UINT8"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821
UInt16 = NewType("UInt16", AbstractType["UINT16"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821
UInt32 = NewType("UInt32", AbstractType["UINT32"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821

Int8 = NewType("Int8", AbstractType["INT8"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821
Int32 = NewType("Int32", AbstractType["INT32"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821
Int64 = NewType("Int64", AbstractType["INT64"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821

Float32 = NewType("Float32", AbstractType["FLOAT32"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821
Float64 = NewType("Float64", AbstractType["FLOAT64"])  # type: ignore[misc,name-defined,type-arg] # noqa: F821

# Mapping for class-based types that don't use Annotated metadata
_CLASS_TYPE_MAPPING: dict[type[Any], AbstractTypeDefinition] = {
    Geometry: AbstractTypeRegistry.TYPES["GEOMETRY"],
}


# Utility functions for easy access
def get_target_type(concrete_type: type[Any], language: str) -> str | None:
    """Get target language type for a concrete type."""
    abstract_type_def = get_abstract_type(concrete_type)
    if abstract_type_def:
        return abstract_type_def.target_mappings.get(language)
    return None


def get_abstract_type(
    concrete_type: type[Any],
) -> AbstractTypeDefinition | None:
    """Get the abstract type definition for a concrete type."""
    # For NewType with Annotated, check if it has __metadata__
    if hasattr(concrete_type, "__metadata__"):
        for item in concrete_type.__metadata__:
            if isinstance(item, AbstractTypeDefinition):
                return item

    # For NewType, check if __supertype__ has metadata
    if hasattr(concrete_type, "__supertype__"):
        return get_abstract_type(concrete_type.__supertype__)

    # Fallback for class-based types that don't use Annotated metadata
    return _CLASS_TYPE_MAPPING.get(concrete_type)
