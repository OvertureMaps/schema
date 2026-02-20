"""Error formatting and grouping for validation errors."""

from collections import defaultdict
from typing import Any

from pydantic import BaseModel
from rich.console import Console

from .data_display import (
    DEFAULT_CONTEXT_SIZE,
    create_feature_display,
    extract_feature_data,
    format_path,
    select_context_fields,
)
from .type_analysis import (
    StructuralTuple,
    UnionMetadata,
    extract_discriminator_path,
    get_item_index,
    get_or_create_structural_tuple,
    infer_model_from_error,
)
from .types import ErrorLocation, ValidationErrorDict


def group_errors_by_discriminator(
    errors: list[ValidationErrorDict],
    metadata: UnionMetadata,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> dict[ErrorLocation, list[ValidationErrorDict]]:
    """Group validation errors by their discriminator path.

    Errors are grouped by which model variant they're associated with, as indicated
    by their discriminator path. This allows the CLI to show only errors for the most
    likely intended type, rather than overwhelming the user with errors from all
    possible union variants.

    Args
    ----
        errors: List of Pydantic validation error dicts
        metadata: Pre-computed UnionMetadata from introspect_union()
        structural_cache: Optional cache for structural tuple computation

    Returns
    -------
        Dictionary mapping discriminator paths to lists of errors

    Examples
    --------
        >>> from typing import Annotated, Union
        >>> from pydantic import Field
        >>> from overture.schema.buildings import Building, BuildingPart
        >>> from overture.schema.validation.type_analysis import introspect_union
        >>> BuildingUnion = Annotated[
        ...     Union[Building, BuildingPart],
        ...     Field(discriminator='type')
        ... ]
        >>> # Errors from validating two buildings with different issues
        >>> errors = [
        ...     {'loc': (0, 'tagged-union[type]', 'building', 'height'), 'msg': 'Field required'},
        ...     {'loc': (0, 'tagged-union[type]', 'building', 'id'), 'msg': 'Field required'},
        ...     {'loc': (1, 'tagged-union[type]', 'building', 'geometry'), 'msg': 'Invalid geometry'},
        ... ]
        >>> metadata = introspect_union(BuildingUnion)
        >>> groups = group_errors_by_discriminator(errors, metadata)
        >>> list(groups.keys())
        [('building',)]
        >>> len(groups[('building',)])
        3

        >>> # Errors from ambiguous data matching multiple types
        >>> errors = [
        ...     {'loc': ('tagged-union[type]', 'building', 'height'), 'msg': 'Field required'},
        ...     {'loc': ('tagged-union[type]', 'building_part', 'building_id'), 'msg': 'Field required'},
        ... ]
        >>> groups = group_errors_by_discriminator(errors, metadata)
        >>> len(groups)  # Two groups - one for each potential type
        2
        >>> ('building',) in groups
        True
        >>> ('building_part',) in groups
        True
    """
    groups: dict[ErrorLocation, list[ValidationErrorDict]] = defaultdict(list)

    for error in errors:
        loc = error["loc"]
        try:
            structural = get_or_create_structural_tuple(loc, metadata, structural_cache)
            disc_path = extract_discriminator_path(loc, structural)
            groups[disc_path].append(error)
        except (KeyError, TypeError, IndexError):
            # Structural analysis can fail for unexpected error path formats
            # (e.g., new Pydantic union markers). Group under empty path as fallback.
            groups[()].append(error)

    return dict(groups)


def analyze_collection_heterogeneity(
    errors: list[ValidationErrorDict],
    metadata: UnionMetadata,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> tuple[dict[int, type[BaseModel] | None], bool]:
    """Analyze a collection to detect type heterogeneity.

    Args
    ----
        errors: List of Pydantic validation error dicts
        metadata: Pre-computed UnionMetadata from introspect_union()
        structural_cache: Optional cache for structural tuple computation

    Returns
    -------
        Tuple of (item_types, is_heterogeneous) where:
        - item_types: Dict mapping item index to inferred model type
        - is_heterogeneous: True if collection contains multiple model types
    """
    # Group errors by item index
    item_errors: dict[int | None, list[ValidationErrorDict]] = defaultdict(list)
    for error in errors:
        item_idx = get_item_index(error["loc"])
        item_errors[item_idx].append(error)

    # Infer the most likely type for each item
    # Use heuristic: type with FEWEST errors is most likely correct
    item_types: dict[int, type[BaseModel] | None] = {}
    for item_idx, item_error_list in item_errors.items():
        if item_idx is None:
            continue

        # Group this item's errors by inferred type
        errors_by_type: dict[type[BaseModel], list[ValidationErrorDict]] = defaultdict(
            list
        )
        for error in item_error_list:
            inferred_type = infer_model_from_error(error, metadata, structural_cache)
            if inferred_type is not None:
                errors_by_type[inferred_type].append(error)

        if errors_by_type:
            # Select the type with the FEWEST errors (smallest edit distance)
            item_types[item_idx] = min(
                errors_by_type.keys(), key=lambda t: len(errors_by_type[t])
            )
        else:
            item_types[item_idx] = None

    # Check if the collection is heterogeneous
    unique_types = {t for t in item_types.values() if t is not None}
    is_heterogeneous = len(unique_types) > 1

    return item_types, is_heterogeneous


def select_most_likely_errors(
    error_groups: dict[ErrorLocation, list[ValidationErrorDict]],
    metadata: UnionMetadata | None = None,
    all_errors: list[ValidationErrorDict] | None = None,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> tuple[list[ValidationErrorDict], bool, bool, dict[int, type[BaseModel] | None]]:
    """Select the error group(s) most likely to be the intended model.

    Uses heuristic: the group with the fewest errors is most likely correct,
    as it requires the fewest changes to make the data valid.

    When multiple groups have the same minimum error count (a tie), returns
    all tied groups to indicate ambiguity to the user.

    For heterogeneous collections, returns ALL errors since different items
    may have different intended types.

    Args
    ----
        error_groups: Dictionary mapping discriminator paths to error lists
        metadata: Optional UnionMetadata for heterogeneity detection
        all_errors: Optional list of all errors for heterogeneity analysis
        structural_cache: Optional cache for structural tuple computation

    Returns
    -------
        Tuple of (errors_list, is_tied, is_heterogeneous, item_types) where:
        - errors_list: List of errors to display
        - is_tied: True if multiple groups had the same minimum error count
        - is_heterogeneous: True if collection contains multiple model types
        - item_types: Dict mapping item index to inferred model type
    """
    if not error_groups:
        return [], False, False, {}

    # Check for heterogeneous collections
    is_heterogeneous = False
    item_types: dict[int, type[BaseModel] | None] = {}
    if metadata is not None and all_errors is not None:
        item_types, is_heterogeneous = analyze_collection_heterogeneity(
            all_errors, metadata, structural_cache
        )

    # For heterogeneous collections, return only errors matching each item's inferred type
    if is_heterogeneous and all_errors is not None:
        filtered_errors = []
        for error in all_errors:
            item_idx = get_item_index(error["loc"])
            if item_idx is not None and item_idx in item_types:
                # Only include this error if it matches the inferred type for this item
                if metadata is not None:
                    error_type = infer_model_from_error(
                        error, metadata, structural_cache
                    )
                    if error_type == item_types[item_idx]:
                        filtered_errors.append(error)
            else:
                # Non-list errors or items without inferred type - include them
                filtered_errors.append(error)

        return filtered_errors, False, True, item_types

    # Find the minimum error count
    min_error_count = min(len(errors) for errors in error_groups.values())

    # Get all groups with the minimum error count
    tied_groups = [
        errors for errors in error_groups.values() if len(errors) == min_error_count
    ]

    # Flatten all errors from tied groups
    flattened_errors = [error for group in tied_groups for error in group]

    # Indicate if there was a tie
    is_tied = len(tied_groups) > 1

    return flattened_errors, is_tied, is_heterogeneous, item_types


def get_effective_message(error: ValidationErrorDict) -> str:
    """Return the effective error message, preferring ctx["error"] over msg."""
    msg = error["msg"]
    ctx = error.get("ctx", {})
    if "error" in ctx:
        return str(ctx["error"])
    return msg


_DISPLAYABLE_STRUCT_TYPES = ("list_index", "field")


def _filter_union_markers(
    loc: ErrorLocation,
    metadata: UnionMetadata | None,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None,
) -> list[str | int]:
    """Filter Pydantic union markers from an error location path.

    Keeps only list indices and field names, stripping out internal
    discriminator and model markers that are noise in user-facing output.
    """
    if metadata is None:
        return list(loc)
    try:
        structural = get_or_create_structural_tuple(loc, metadata, structural_cache)
        return [
            element
            for element, struct_type in zip(loc, structural, strict=False)
            if struct_type in _DISPLAYABLE_STRUCT_TYPES
        ]
    except (KeyError, TypeError, IndexError):
        return list(loc)


def format_validation_errors_verbose(
    errors: list[ValidationErrorDict],
    console: Console,
    metadata: UnionMetadata | None = None,
    item_type: type[BaseModel] | None = None,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
    original_data: dict[str, Any] | list[Any] | None = None,
    item_index: int | None = None,
    show_fields: list[str] | None = None,
) -> bool:
    """Format and display multiple validation errors for a single item in verbose mode.

    Args
    ----
        errors: List of validation errors for this item
        console: Rich Console instance for output
        metadata: Pre-computed UnionMetadata from introspect_union() (optional)
        item_type: The inferred type for this item
        structural_cache: Optional cache for structural tuple computation
        original_data: Original input data for extracting feature details
        item_index: Index of item in collection
        show_fields: List of field names to display alongside errors

    Returns
    -------
        True if errors were displayed, False otherwise
    """
    if not errors or not original_data:
        return False

    # Extract item index from first error if not provided
    if item_index is None:
        item_index = get_item_index(errors[0]["loc"])

    # Extract flattened feature data
    feature = extract_feature_data(original_data, item_index)
    if not feature:
        return False

    # Collect all error paths and messages
    error_tuples: list[tuple[list[str | int], str]] = []
    for error in errors:
        loc = error["loc"]
        msg = get_effective_message(error)

        error_path = _filter_union_markers(loc, metadata, structural_cache)

        # Strip out the list index since we've already extracted that feature
        if error_path and isinstance(error_path[0], int):
            error_path = error_path[1:]

        error_tuples.append((error_path, msg))

    # Select context fields for all errors
    # Merge context from all error paths
    context_size = DEFAULT_CONTEXT_SIZE
    selected_fields: dict[str, Any] = {}

    for error_path, _ in error_tuples:
        context = select_context_fields(
            feature, error_path, context_size=context_size, pinned_fields=show_fields
        )
        selected_fields.update(context)

    if not selected_fields:
        return False

    type_name = item_type.__name__ if item_type else None
    panel = create_feature_display(
        selected_fields,
        error_tuples,
        item_index=item_index,
        item_type=type_name,
        show_fields=show_fields,
        feature=feature,
    )
    console.print(panel)
    console.print()
    return True


def format_validation_error(
    error: ValidationErrorDict,
    console: Console,
    metadata: UnionMetadata | None = None,
    show_model_hint: bool = False,
    item_type: type[BaseModel] | None = None,
    show_item_type: bool = False,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> None:
    """Format and print a single validation error.

    Args
    ----
        error: Pydantic validation error dict
        console: Rich Console instance for output
        metadata: Pre-computed UnionMetadata from introspect_union() (optional)
        show_model_hint: Show which model was selected for validation (first error only)
        item_type: The inferred type for this item (always provided if available)
        show_item_type: Whether to display the item type in the path (True for heterogeneous collections)
        structural_cache: Optional cache for structural tuple computation
    """
    loc = error["loc"]

    # Determine which model was selected for this error
    selected_model = None
    if metadata is not None and show_model_hint:
        try:
            structural = get_or_create_structural_tuple(loc, metadata, structural_cache)

            # Look for discriminator value in the location path
            for element, struct_type in zip(loc, structural, strict=False):
                if struct_type == "discriminator" and isinstance(element, str):
                    selected_model = metadata.discriminator_to_model.get(element)
                    break
                elif struct_type == "model" and isinstance(element, str):
                    selected_model = metadata.model_name_to_model.get(element)
                    break
        except (KeyError, TypeError, IndexError):
            # Structural analysis can fail for unexpected error path formats
            pass

    filtered_loc = _filter_union_markers(loc, metadata, structural_cache)

    # Convert to dot-separated path
    path_str = format_path(filtered_loc) or "(root)"

    # Add item type annotation if requested (for heterogeneous collections)
    if show_item_type and item_type is not None:
        path_str = f"{path_str} [dim]({item_type.__name__})[/dim]"

    # Show model hint if this is the first error in a group
    if selected_model is not None:
        model_name = selected_model.__name__
        console.print(f"  [dim]Probable type:[/dim] {model_name}", style="blue")
        console.print()

    # Format the error message
    msg = get_effective_message(error)
    input_value = error.get("input")

    # Suppress input value when the message came from a nested error context,
    # since the raw input is misleading in that case.
    if "error" in error.get("ctx", {}):
        input_value = None

    console.print(f"  {path_str}", style="cyan")
    console.print(f"    → {msg}", style="yellow")

    # Show input value if present and not too large
    if input_value is not None:
        value_str = (
            repr(input_value)
            if not isinstance(input_value, str)
            else f"'{input_value}'"
        )
        prefix = "    → Got: "
        if len(value_str) <= console.width - len(prefix):
            console.print(f"{prefix}{value_str}", style="dim")
    console.print()
