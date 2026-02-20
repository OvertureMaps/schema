"""Type introspection and structural analysis for union types."""

import inspect
from dataclasses import dataclass
from typing import Annotated as AnnotatedType
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

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
    # Nested union metadata for union members that are themselves unions
    nested_unions: dict[str, "UnionMetadata"]


def _process_union_member(
    member: Any,  # noqa: ANN401
    discriminator_to_model: dict[str, type[BaseModel]],
    model_name_to_model: dict[str, type[BaseModel]],
    nested_unions: dict[str, UnionMetadata],
) -> None:
    """Process a single union member, handling nesting recursively.

    Args
    ----
        member: A union member type (could be Annotated, BaseModel, or nested union)
        discriminator_to_model: Dict to populate with discriminator value mappings
        model_name_to_model: Dict to populate with model name mappings
        nested_unions: Dict to populate with nested union metadata
    """
    member_origin = get_origin(member)

    # Case 1: Annotated type (might contain nested union or Tag)
    if member_origin is AnnotatedType:
        member_args = get_args(member)
        if not member_args:
            return

        # Check for discriminator in annotations
        has_discriminator = any(
            isinstance(metadata, FieldInfo) and hasattr(metadata, "discriminator")
            for metadata in member_args[1:]
        )

        if has_discriminator or get_origin(member_args[0]) is not None:
            # Nested union (with or without discriminator)
            nested_metadata = introspect_union(member)
            nested_unions[str(member)] = nested_metadata
            discriminator_to_model.update(nested_metadata.discriminator_to_model)
            return

        # Unwrap Annotated to get the actual type (e.g., Annotated[Building, Tag('building')])
        # and process it recursively
        _process_union_member(
            member_args[0], discriminator_to_model, model_name_to_model, nested_unions
        )
        return

    # Case 2: BaseModel class
    if inspect.isclass(member) and issubclass(member, BaseModel):
        model_name_to_model[member.__name__] = member

        # Extract discriminator values from known discriminator fields only
        # Restrict to known discriminator names to avoid false positives from other Literal fields
        discriminator_fields = ("type", "theme", "subtype")
        for field_name, field_info in member.model_fields.items():
            if field_name not in discriminator_fields:
                continue
            annotation = field_info.annotation
            if get_origin(annotation) is Literal:
                literal_args = get_args(annotation)
                if literal_args:
                    discriminator_to_model[literal_args[0]] = member


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
    origin = get_origin(union_type)
    if origin is list:
        args = get_args(union_type)
        if args:
            # Recursively introspect the list element type
            return introspect_union(args[0])

    # Check if this is an Annotated type with a discriminator
    discriminator_field = None
    actual_union = union_type

    # Unwrap Annotated ONLY if the top level is Annotated
    if origin is AnnotatedType:
        # This is Annotated[Union[...], ...]
        args = get_args(union_type)
        if args:
            # First arg is the actual type, rest are metadata
            actual_union = args[0]
            # Look for Field with discriminator in metadata
            for metadata in args[1:]:
                if isinstance(metadata, FieldInfo) and hasattr(
                    metadata, "discriminator"
                ):
                    disc = metadata.discriminator
                    # discriminator can be a string or Discriminator object
                    discriminator_field = str(disc) if disc is not None else None
                    break

    # Get union members
    union_origin = get_origin(actual_union)
    if union_origin is None:
        # Not a union, might be a single model
        union_members = [actual_union]
    else:
        union_members = list(get_args(actual_union))

    discriminator_to_model: dict[str, type[BaseModel]] = {}
    model_name_to_model: dict[str, type[BaseModel]] = {}
    nested_unions: dict[str, UnionMetadata] = {}

    # Process each union member
    for member in union_members:
        _process_union_member(
            member, discriminator_to_model, model_name_to_model, nested_unions
        )

    return UnionMetadata(
        is_discriminated=discriminator_field is not None,
        discriminator_field=discriminator_field,
        discriminator_to_model=discriminator_to_model,
        model_name_to_model=model_name_to_model,
        nested_unions=nested_unions,
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
