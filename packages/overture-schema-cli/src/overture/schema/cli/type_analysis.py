"""Type introspection and structural analysis for union types."""

from dataclasses import dataclass
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel

from overture.schema.system.typing_util import (
    discriminator_values,
    model_variants,
    union_discriminator,
)

from .types import ErrorLocation, ValidationErrorDict

# Type aliases for structural tuple elements
StructuralElement = Literal["list_index", "union", "model", "discriminator", "field"]
StructuralTuple = tuple[StructuralElement, ...]


@dataclass
class UnionMetadata:
    """Metadata about a union type's structure."""

    is_discriminated: bool
    discriminator_field: str | None
    # Map discriminator values to their corresponding model types
    discriminator_to_model: dict[str, type[BaseModel]]
    # Map model class names to their types (for non-discriminated unions)
    model_name_to_model: dict[str, type[BaseModel]]


def _discriminator_keys(model: type[BaseModel], field_name: str) -> tuple[str, ...]:
    """Return the normalized discriminator keys a model field accepts.

    Delegates to `typing_util.discriminator_values` -- the same convention
    codegen's discriminator mapping uses, and the form pydantic reports in
    error locs. Pydantic accepts multi-value literal tags, so a member may
    contribute several keys; all of them must route to the model.
    """
    field_info = model.model_fields.get(field_name)
    if field_info is None or field_info.annotation is None:
        return ()
    return discriminator_values(field_info.annotation) or ()


def introspect_union(union_type: Any) -> UnionMetadata:  # noqa: ANN401
    """Introspect a union type to extract structural information.

    Analyzes a union type (which may be discriminated or non-discriminated) to
    extract metadata about its structure, including discriminator fields, model
    mappings, and nested union information. This metadata is used for structural
    analysis of validation error paths.

    Args
    ----
        union_type: A union type (may be Annotated with discriminator)

    Returns
    -------
        UnionMetadata describing the structure of the union

    Examples
    --------
        >>> from typing import Annotated, Union
        >>> from pydantic import Field
        >>> from overture.schema.buildings import Building, BuildingPart
        >>> from overture.schema.transportation import Segment, Connector
        >>> # Discriminated union with 'type' field
        >>> BuildingUnion = Annotated[
        ...     Union[Building, BuildingPart],
        ...     Field(discriminator='type')
        ... ]
        >>> metadata = introspect_union(BuildingUnion)
        >>> metadata.is_discriminated
        True
        >>> metadata.discriminator_field
        'type'
        >>> 'building' in metadata.discriminator_to_model
        True

        >>> # Non-discriminated union (using plain Union without discriminator)
        >>> from overture.schema.transportation import Connector
        >>> PlainUnion = Union[Building, Connector]
        >>> metadata = introspect_union(PlainUnion)
        >>> metadata.is_discriminated
        False
        >>> 'Connector' in metadata.model_name_to_model
        True

        >>> # List of discriminated union (unwraps to element type)
        >>> FeatureList = list[BuildingUnion]
        >>> metadata = introspect_union(FeatureList)
        >>> metadata.is_discriminated
        True
    """
    # Check if this is a list type - unwrap to get the element type
    if get_origin(union_type) is list:
        args = get_args(union_type)
        if args:
            # Recursively introspect the list element type
            return introspect_union(args[0])

    variants = model_variants(union_type)

    model_name_to_model = {v.model.__name__: v.model for v in variants}

    # Each variant's discriminator_path carries every discriminator field on the
    # way to the model (e.g. ("type", "subtype") for a nested discriminated
    # union), so nested models are reachable by the parent's discriminator
    # values as well as their own.
    discriminator_to_model: dict[str, type[BaseModel]] = {}
    for variant in variants:
        for field_name in variant.discriminator_path:
            for key in _discriminator_keys(variant.model, field_name):
                discriminator_to_model[key] = variant.model

    discriminator_field = union_discriminator(union_type)
    return UnionMetadata(
        is_discriminated=discriminator_field is not None,
        discriminator_field=discriminator_field,
        discriminator_to_model=discriminator_to_model,
        model_name_to_model=model_name_to_model,
    )


def get_or_create_structural_tuple(
    loc: ErrorLocation,
    metadata: UnionMetadata,
    cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> StructuralTuple:
    """Get structural tuple with optional caching for systematic errors.

    When validating collections with systematic errors (e.g., same field missing
    across many rows), this cache dramatically reduces redundant classification work.

    Args
    ----
        loc: The location tuple from a Pydantic validation error
        metadata: Pre-computed UnionMetadata from introspect_union()
        cache: Optional dict to cache results (same cache used across all errors)

    Returns
    -------
        Tuple of same length as loc with structural labels for each element
    """
    if cache is not None and loc in cache:
        return cache[loc]

    structural = create_structural_tuple(loc, metadata)

    if cache is not None:
        cache[loc] = structural

    return structural


def create_structural_tuple(
    loc: ErrorLocation,
    metadata: UnionMetadata,
) -> StructuralTuple:
    """Create a structural tuple parallel to error['loc'] describing each element.

    The structural tuple helps identify which parts of an error path are:
    - list_index: Indices from array iteration
    - union: Pydantic's tagged union markers (e.g., 'tagged-union[type]')
    - discriminator: Discriminator values (e.g., 'building', 'segment')
    - model: Model class names in non-discriminated unions (e.g., 'Segment')
    - field: Actual data field names (e.g., 'height', 'id')

    Args
    ----
        loc: The location tuple from a Pydantic validation error
        metadata: Pre-computed UnionMetadata from introspect_union()

    Returns
    -------
        Tuple of same length as loc with structural labels for each element

    Examples
    --------
        >>> from typing import Annotated, Union
        >>> from pydantic import Field
        >>> from overture.schema.buildings import Building, BuildingPart
        >>> from overture.schema.transportation import Connector
        >>> BuildingUnion = Annotated[
        ...     Union[Building, BuildingPart],
        ...     Field(discriminator='type')
        ... ]
        >>> PlainUnion = Union[Building, Connector]
        >>> # Error in first feature of a list, in a building's height field
        >>> loc = (0, 'tagged-union[type]', 'building', 'height')
        >>> metadata = introspect_union(BuildingUnion)
        >>> create_structural_tuple(loc, metadata)
        ('list_index', 'union', 'discriminator', 'field')

        >>> # Error in a non-discriminated union (uses model name)
        >>> loc = ('Connector', 'connectors', 0)
        >>> metadata = introspect_union(PlainUnion)
        >>> create_structural_tuple(loc, metadata)
        ('model', 'field', 'list_index')

        >>> # Simple field error (no union involved)
        >>> loc = ('id',)
        >>> metadata = introspect_union(Building)
        >>> create_structural_tuple(loc, metadata)
        ('field',)
    """

    def classify(element: str | int) -> StructuralElement:
        """Classify a single location element."""
        if isinstance(element, int):
            return "list_index"
        if isinstance(element, str):
            # Pydantic generates various union marker formats
            if (
                element.startswith("tagged-union[")
                or element.startswith("function-after[")
                or element.startswith("function-wrap[")
            ):
                return "union"
            if element in metadata.model_name_to_model:
                return "model"
            if element in metadata.discriminator_to_model:
                return "discriminator"
        return "field"

    return tuple(classify(e) for e in loc)


def get_item_index(loc: ErrorLocation) -> int | None:
    """Extract the top-level list index from an error location, if present.

    Args
    ----
        loc: The location tuple from a Pydantic validation error

    Returns
    -------
        The list index if the error is within a list item, otherwise None
    """
    if loc and isinstance(loc[0], int):
        return loc[0]
    return None


def infer_model_from_error(
    error: ValidationErrorDict,
    metadata: UnionMetadata,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> type[BaseModel] | None:
    """Infer the model type that an error is associated with.

    Uses the LAST (most specific) discriminator or model name found in the
    error path, as nested unions may have multiple discriminators.

    Args
    ----
        error: Pydantic validation error dict
        metadata: Pre-computed UnionMetadata from introspect_union()
        structural_cache: Optional cache for structural tuple computation

    Returns
    -------
        The inferred model type, or None if it cannot be determined
    """
    loc = error["loc"]
    try:
        structural = get_or_create_structural_tuple(loc, metadata, structural_cache)

        # Look for discriminator value or model name in the location path
        # Use the LAST one found (most specific) rather than the first
        inferred_model = None
        for element, struct_type in zip(loc, structural, strict=False):
            if struct_type == "discriminator" and isinstance(element, str):
                model = metadata.discriminator_to_model.get(element)
                if model is not None:
                    inferred_model = model
            elif struct_type == "model" and isinstance(element, str):
                model = metadata.model_name_to_model.get(element)
                if model is not None:
                    inferred_model = model

        return inferred_model
    except (KeyError, TypeError, IndexError):
        # Structural analysis can fail for unexpected error path formats
        pass

    return None


def extract_discriminator_path(
    loc: ErrorLocation,
    structural: StructuralTuple,
) -> ErrorLocation:
    """Extract the discriminator path from a location tuple.

    The discriminator path includes model names and discriminator values - everything
    up to (but not including) the first field. List indices and union markers are
    excluded to prevent false ambiguity when validating lists of features or complex
    union structures.

    This path uniquely identifies which model variant was selected during validation,
    allowing errors to be grouped by the type they're associated with.

    Args
    ----
        loc: The location tuple from a Pydantic validation error
        structural: The parallel structural tuple

    Returns
    -------
        The discriminator path portion of the location tuple (excluding list_index and union)

    Examples
    --------
        >>> # Discriminated union with field error
        >>> loc = (0, 'tagged-union[type]', 'building', 'height')
        >>> structural = ('list_index', 'union', 'discriminator', 'field')
        >>> extract_discriminator_path(loc, structural)
        ('building',)

        >>> # Non-discriminated union
        >>> loc = ('Segment', 'connectors', 0)
        >>> structural = ('model', 'field', 'list_index')
        >>> extract_discriminator_path(loc, structural)
        ('Segment',)

        >>> # Root field error (no discriminator)
        >>> loc = ('id',)
        >>> structural = ('field',)
        >>> extract_discriminator_path(loc, structural)
        ()

        >>> # Multiple list items with same error type are grouped together
        >>> loc1 = (0, 'tagged-union[type]', 'building', 'height')
        >>> loc2 = (5, 'tagged-union[type]', 'building', 'height')
        >>> structural = ('list_index', 'union', 'discriminator', 'field')
        >>> extract_discriminator_path(loc1, structural)
        ('building',)
        >>> extract_discriminator_path(loc2, structural)
        ('building',)
        >>> # Both produce same discriminator path despite different list indices and union markers
    """
    discriminator_path = []
    for element, struct_type in zip(loc, structural, strict=False):
        if struct_type == "field":
            # Stop at the first field
            break
        if struct_type not in ("list_index", "union"):
            # Include only discriminator and model elements
            discriminator_path.append(element)
    return tuple(discriminator_path)
