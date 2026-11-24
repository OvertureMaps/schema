"""Error formatting and grouping for validation errors."""

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel
from rich.console import Console

from .data_display import (
    create_feature_display,
    extract_feature_data,
    select_context_fields,
)
from .type_analysis import (
    StructuralTuple,
    UnionMetadata,
    extract_discriminator_path,
    get_item_index,
    get_or_create_structural_tuple,
    infer_model_from_error,
    models_in_path,
)
from .types import ErrorLocation, ValidationErrorDict


def group_errors_by_discriminator(
    errors: list[ValidationErrorDict],
    metadata: UnionMetadata,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> dict[ErrorLocation, list[ValidationErrorDict]]:
    """Group validation errors by the model variant they belong to.

    Errors are grouped by which model variant they're associated with: the names of
    the models their location selects, or their discriminator path when it selects
    none. This allows the CLI to show only errors for the most likely intended type,
    rather than overwhelming the user with errors from all possible union variants.

    Parameters
    ----------
    errors : list[ValidationErrorDict]
        List of Pydantic validation error dicts
    metadata : UnionMetadata
        Pre-computed UnionMetadata from introspect_union()
    structural_cache : dict[ErrorLocation, StructuralTuple] | None
        Optional cache for structural tuple computation

    Returns
    -------
    dict[ErrorLocation, list[ValidationErrorDict]]
        Dictionary mapping group keys to lists of errors

    Examples
    --------
        >>> from typing import Annotated, Union
        >>> from pydantic import Field
        >>> from overture.schema.buildings import Building, BuildingPart
        >>> from overture.schema.cli.type_analysis import introspect_union
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
        [('Building',)]
        >>> len(groups[('Building',)])
        3

        >>> # Errors from ambiguous data matching multiple types
        >>> errors = [
        ...     {'loc': ('tagged-union[type]', 'building', 'height'), 'msg': 'Field required'},
        ...     {'loc': ('tagged-union[type]', 'building_part', 'building_id'), 'msg': 'Field required'},
        ... ]
        >>> groups = group_errors_by_discriminator(errors, metadata)
        >>> len(groups)  # Two groups - one for each potential type
        2
        >>> ('Building',) in groups
        True
        >>> ('BuildingPart',) in groups
        True
    """
    groups: dict[ErrorLocation, list[ValidationErrorDict]] = {}

    for error in errors:
        loc = error["loc"]
        try:
            structural = get_or_create_structural_tuple(loc, metadata, structural_cache)
            group_key = _group_key(loc, structural, metadata, structural_cache)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(error)
        except (KeyError, TypeError, IndexError):
            # Structural analysis can fail for unexpected error path formats
            # (e.g., new Pydantic union markers). Group under the empty key as fallback.
            if () not in groups:
                groups[()] = []
            groups[()].append(error)

    return groups


def _group_key(
    loc: ErrorLocation,
    structural: StructuralTuple,
    metadata: UnionMetadata,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None,
) -> ErrorLocation:
    # Two nested unions can share a discriminator value ("water" is a base type and a
    # segment subtype), so the value alone would put both types' errors in one group.
    # Name the models the value resolves to instead.
    models = models_in_path(loc, metadata, structural_cache)
    if models:
        return tuple(model.__name__ for model in models)
    return extract_discriminator_path(loc, structural)


# How much an error says about its item, lowest first: a sibling union's tag error
# that `_is_redundant_tag_error` finds redundant, a missing tag, any other error.
_REDUNDANT_TAG_RANK = 0
_MISSING_TAG_RANK = 1
_ERROR_RANK = 2


def _branch_rejections(
    error_groups: dict[ErrorLocation, list[ValidationErrorDict]],
    metadata: UnionMetadata | None,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> dict[int | None, dict[ErrorLocation, set[str]]]:
    """Map each item's branches to the tag fields each rejected the item on.

    A branch rejects an item's tag with a `literal_error` on one of the branch's
    own tag fields (`theme`, `type`, a segment's `subtype`), not on a nested
    field of the same name. A branch that rejected none accepted the item as its
    type, and only its other fields are wrong.

    Parameters
    ----------
    error_groups : dict[ErrorLocation, list[ValidationErrorDict]]
        Mapping of group keys to their error lists
    metadata : UnionMetadata | None
        The union the items were validated against, which names the tag fields
    structural_cache : dict[ErrorLocation, StructuralTuple] | None
        Optional cache for structural tuple computation

    Returns
    -------
    dict[int | None, dict[ErrorLocation, set[str]]]
        For each item, the rejected tag fields of each branch that has errors
    """
    rejections: dict[int | None, dict[ErrorLocation, set[str]]] = defaultdict(dict)
    for group_key, errors in error_groups.items():
        for error in errors:
            loc = error["loc"]
            rejected = rejections[get_item_index(loc)].setdefault(group_key, set())
            if metadata is not None and _rejects_branch_tag(
                error, metadata, structural_cache
            ):
                rejected.add(str(loc[-1]))
    return rejections


def _rejects_branch_tag(
    error: ValidationErrorDict,
    metadata: UnionMetadata,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None,
) -> bool:
    """Whether *error* rejects the item's value for a top-level tag field of a branch."""
    loc = error["loc"]
    if error.get("type") != "literal_error" or loc[-1] not in metadata.tag_values:
        return False
    structural = get_or_create_structural_tuple(loc, metadata, structural_cache)
    return len(structural) >= 2 and structural[-2] in (
        "model",
        "discriminator",
        "union",
    )


def _is_redundant_tag_error(
    error: ValidationErrorDict,
    item_rejections: Iterable[set[str]],
    metadata: UnionMetadata | None,
) -> bool:
    """Whether a sibling union's `union_tag_invalid` adds nothing to the item's errors.

    It adds nothing when some model takes the rejected tag in the union's field, or
    when a branch rejected none of the item's tags but that field: the branch then
    accepted the item, or names the value it expects there (`type` "segmnt" on a
    road segment). A branch that also rejects another tag (a water segment rejecting
    a base water's `theme`) is not the item's type, and the tag error states the
    mistake. Without *metadata* the union's field and the tags models take are
    unknown, so only a branch that rejected nothing makes the error redundant.

    Parameters
    ----------
    error : ValidationErrorDict
        A `union_tag_invalid` error from a sibling union
    item_rejections : Iterable[set[str]]
        The tag fields each branch rejected the item on
    metadata : UnionMetadata | None
        The union the item was validated against

    Returns
    -------
    bool
        True if the error is redundant
    """
    field = None
    known_tags: set[str] = set()
    if metadata is not None:
        loc = error["loc"]
        union_marker = loc[-1] if loc and isinstance(loc[-1], str) else None
        field = metadata.discriminator_field_for(union_marker)
        known_tags = metadata.tag_values.get(field, set()) if field else set()
    if error.get("ctx", {}).get("tag") in known_tags:
        return True
    return any(rejected <= {field} for rejected in item_rejections)


def _suppress_sibling_tag_noise(
    error_groups: dict[ErrorLocation, list[ValidationErrorDict]],
    metadata: UnionMetadata | None = None,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> dict[ErrorLocation, list[ValidationErrorDict]]:
    """Drop discriminator noise from sibling branches for items that matched a type.

    When validating against a union that mixes a tagged-union with other
    (also discriminated) members, an item that cleanly matches one branch still
    produces a tag error from every *sibling* branch whose discriminator it fails
    to satisfy: `union_tag_not_found` when the item lacks the sibling's
    discriminator field, `union_tag_invalid` when it has the field with a value
    the sibling does not know (a segment's `type` is "segment", which the union
    discriminated on `type` does not list). Those errors carry an empty group
    key `()`, forming a spurious group that can tie with the real match and
    trigger a false "Ambiguous" warning, or, having fewer errors, hide the real
    match entirely.

    Only a tag error in the `()` group is sibling noise. One under a group key
    comes from a union inside the branch the item matched (a road segment's
    `vehicle` selector with an unknown `dimension`) and counts as any other
    error. So does a `union_tag_invalid` that is not redundant (see
    `_is_redundant_tag_error`): the item's own `type` or `subtype` is wrong, and
    the tag error names the mistake. This helper keeps, for each list item, only its
    errors of the highest rank: any other error, then `union_tag_not_found`, then
    a redundant `union_tag_invalid`. Groups left empty after filtering are
    dropped.

    Parameters
    ----------
    error_groups : dict[ErrorLocation, list[ValidationErrorDict]]
        Mapping of group keys to their error lists.
    metadata : UnionMetadata | None
        The union the items were validated against, which names the tag fields
        and the tags its models take.
    structural_cache : dict[ErrorLocation, StructuralTuple] | None
        Optional cache for structural tuple computation.

    Returns
    -------
    dict[ErrorLocation, list[ValidationErrorDict]]
        A new error-groups dict with sibling-branch tag noise removed.

    Examples
    --------
        >>> # Item 0 matched Building but the sibling segment union emitted
        >>> # a union_tag_not_found error, creating a spurious () group.
        >>> error_groups = {
        ...     ('Building',): [
        ...         {'loc': (0, 'tagged-union[type]', 'building', 'id'),
        ...          'msg': 'Field required', 'type': 'missing'},
        ...     ],
        ...     (): [
        ...         {'loc': (0, 'tagged-union[subtype]'),
        ...          'msg': 'Unable to extract tag', 'type': 'union_tag_not_found'},
        ...     ],
        ... }
        >>> cleaned = _suppress_sibling_tag_noise(error_groups)
        >>> list(cleaned.keys())  # the () noise group is gone
        [('Building',)]

        >>> # Item 0 matched RoadSegment, and the sibling union discriminated on
        >>> # 'type' emitted union_tag_invalid, because it lists no 'segment' type.
        >>> error_groups = {
        ...     ('RoadSegment',): [
        ...         {'loc': (0, 'tagged-union[subtype]', 'road', 'class'),
        ...          'msg': 'Input should be ...', 'type': 'enum'},
        ...     ],
        ...     (): [
        ...         {'loc': (0, 'tagged-union[type]'),
        ...          'msg': "Input tag 'segment' ...", 'type': 'union_tag_invalid'},
        ...     ],
        ... }
        >>> list(_suppress_sibling_tag_noise(error_groups).keys())
        [('RoadSegment',)]

        >>> # An item whose ONLY error is union_tag_not_found is preserved.
        >>> error_groups = {
        ...     (): [
        ...         {'loc': (2, 'tagged-union[type]'),
        ...          'msg': 'Unable to extract tag', 'type': 'union_tag_not_found'},
        ...     ],
        ... }
        >>> _suppress_sibling_tag_noise(error_groups) == error_groups
        True
    """
    rejections = _branch_rejections(error_groups, metadata, structural_cache)

    def rank(group_key: ErrorLocation, error: ValidationErrorDict) -> int:
        # Only a tag error with an empty group key comes from a sibling union. One
        # under a group key is inside the branch the item matched.
        if group_key:
            return _ERROR_RANK
        error_type = error.get("type", "")
        if error_type == "union_tag_not_found":
            return _MISSING_TAG_RANK
        if error_type != "union_tag_invalid":
            return _ERROR_RANK
        item_rejections = rejections.get(get_item_index(error["loc"]), {})
        # A plain model's errors have no group key; only a named branch can make a
        # sibling union's tag error redundant.
        named = [rejected for key, rejected in item_rejections.items() if key]
        if _is_redundant_tag_error(error, named, metadata):
            return _REDUNDANT_TAG_RANK
        return _ERROR_RANK

    ranked = [
        (group_key, error, rank(group_key, error))
        for group_key, errors in error_groups.items()
        for error in errors
    ]

    # The highest-ranked error each item has; its lower-ranked tag errors are noise.
    item_rank: dict[int | None, int] = {}
    for _, error, error_rank in ranked:
        item = get_item_index(error["loc"])
        item_rank[item] = max(item_rank.get(item, 0), error_rank)

    cleaned: dict[ErrorLocation, list[ValidationErrorDict]] = {}
    for group_key, error, error_rank in ranked:
        if error_rank == item_rank[get_item_index(error["loc"])]:
            cleaned.setdefault(group_key, []).append(error)
    return cleaned


def select_most_likely_errors(
    error_groups: dict[ErrorLocation, list[ValidationErrorDict]],
    metadata: UnionMetadata | None = None,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
) -> tuple[list[ValidationErrorDict], bool, bool, dict[int, type[BaseModel] | None]]:
    """Select the error group(s) most likely to be the intended model.

    Each item is judged on its own errors, so one item's choice never hides another
    item. An item's most likely group is the one whose branch rejected the fewest
    of the item's tag fields (see `_branch_rejections`), then the one with the
    fewest errors: it requires the fewest changes to make the data valid.

    When an item's groups share the best rank (a tie), returns all its tied groups
    to indicate ambiguity to the user, and the item has no type.

    Before ranking, tag errors from sibling unions are suppressed for any item that
    has a more telling error (see `_suppress_sibling_tag_noise`), so a clean match
    is not falsely reported as ambiguous.

    Parameters
    ----------
    error_groups : dict[ErrorLocation, list[ValidationErrorDict]]
        Dictionary mapping group keys to error lists
    metadata : UnionMetadata | None
        Optional UnionMetadata for tag suppression and item types
    structural_cache : dict[ErrorLocation, StructuralTuple] | None
        Optional cache for structural tuple computation

    Returns
    -------
    tuple[list[ValidationErrorDict], bool, bool, dict[int, type[BaseModel] | None]]
        Tuple of (errors_list, is_tied, is_heterogeneous, item_types) where:
        - errors_list: List of errors to display, in item order
        - is_tied: True if some item's groups tied for the best rank
        - is_heterogeneous: True if the items' types differ
        - item_types: Dict mapping list item index to its selected model type
    """
    if not error_groups:
        return [], False, False, {}

    rejections = _branch_rejections(error_groups, metadata, structural_cache)
    error_groups = _suppress_sibling_tag_noise(error_groups, metadata, structural_cache)

    groups_by_item: dict[int | None, dict[ErrorLocation, list[ValidationErrorDict]]]
    groups_by_item = defaultdict(lambda: defaultdict(list))
    for group_key, errors in error_groups.items():
        for error in errors:
            groups_by_item[get_item_index(error["loc"])][group_key].append(error)

    selected: list[ValidationErrorDict] = []
    is_tied = False
    item_types: dict[int, type[BaseModel] | None] = {}
    # Sort by index: the groups visit items in the order each group first appears.
    for item in sorted(groups_by_item, key=lambda i: -1 if i is None else i):
        item_groups = groups_by_item[item]
        item_rejections = rejections.get(item, {})
        ranks = {
            group_key: (len(item_rejections.get(group_key, set())), len(errors))
            for group_key, errors in item_groups.items()
        }
        best = min(ranks.values())
        tied_groups = [
            errors
            for group_key, errors in item_groups.items()
            if ranks[group_key] == best
        ]
        is_tied = is_tied or len(tied_groups) > 1
        selected.extend(error for group in tied_groups for error in group)
        if item is not None:
            item_types[item] = _selected_type(tied_groups, metadata, structural_cache)

    item_type_set = {t for t in item_types.values() if t is not None}
    return selected, is_tied, len(item_type_set) > 1, item_types


def _selected_type(
    tied_groups: list[list[ValidationErrorDict]],
    metadata: UnionMetadata | None,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None,
) -> type[BaseModel] | None:
    """Return the model an item's one selected group names, if it names one."""
    if metadata is None or len(tied_groups) != 1:
        return None
    return infer_model_from_error(tied_groups[0][0], metadata, structural_cache)


def format_path(filtered_loc: list[str | int]) -> str:
    """Convert filtered location path to dot-separated string.

    Parameters
    ----------
    filtered_loc : list[str | int]
        List of path components (strings and integers)

    Returns
    -------
    str
        Formatted path string (e.g., "properties.name" or "items[0].value")
    """
    path_str = ""
    for i, part in enumerate(filtered_loc):
        if isinstance(part, str):
            if i > 0:
                path_str += "."
            path_str += part
        else:
            path_str += f"[{part}]"

    if not path_str:
        path_str = "(root)"

    return path_str


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

    Parameters
    ----------
    errors : list[ValidationErrorDict]
        List of validation errors for this item
    console : Console
        Rich Console instance for output
    metadata : UnionMetadata | None
        Pre-computed UnionMetadata from introspect_union() (optional)
    item_type : type[BaseModel] | None
        The inferred type for this item
    structural_cache : dict[ErrorLocation, StructuralTuple] | None
        Optional cache for structural tuple computation
    original_data : dict[str, Any] | list[Any] | None
        Original input data for extracting feature details
    item_index : int | None
        Index of item in collection
    show_fields : list[str] | None
        List of field names to display alongside errors

    Returns
    -------
    bool
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
        msg = error["msg"]

        # Extract actual error message from context if available
        ctx = error.get("ctx", {})
        if "error" in ctx:
            msg = ctx["error"]

        # Filter loc to remove union markers
        if metadata is not None:
            try:
                structural = get_or_create_structural_tuple(
                    loc, metadata, structural_cache
                )
                filtered_loc = [
                    element
                    for element, struct_type in zip(loc, structural, strict=False)
                    if struct_type in ("list_index", "field")
                ]
            except (KeyError, TypeError, IndexError):
                # Fall back to unfiltered path on unexpected error formats
                filtered_loc = list(loc)
        else:
            filtered_loc = list(loc)

        # Strip out the list index since we've already extracted that feature
        error_path = list(filtered_loc)
        if error_path and isinstance(error_path[0], int):
            error_path = error_path[1:]

        error_tuples.append((error_path, msg))

    # Select context fields for all errors
    # Merge context from all error paths
    context_size = 1
    selected_fields: dict[str, Any] = {}

    for error_path, _ in error_tuples:
        context = select_context_fields(
            feature, error_path, context_size=context_size, pinned_fields=show_fields
        )
        selected_fields.update(context)

    if selected_fields:
        # Create and display panel with all errors
        # Get type name from item_type if available
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
    else:
        # No fields to display (e.g., root-level discriminator errors)
        return False


def format_validation_error(
    error: ValidationErrorDict,
    console: Console,
    metadata: UnionMetadata | None = None,
    show_model_hint: bool = False,
    item_type: type[BaseModel] | None = None,
    show_item_type: bool = False,
    structural_cache: dict[ErrorLocation, StructuralTuple] | None = None,
    original_data: dict[str, Any] | list[Any] | None = None,
    show_feature_data: bool = False,
) -> None:
    """Format and print a single validation error.

    Parameters
    ----------
    error : ValidationErrorDict
        Pydantic validation error dict
    console : Console
        Rich Console instance for output
    metadata : UnionMetadata | None
        Pre-computed UnionMetadata from introspect_union() (optional)
    show_model_hint : bool
        Show which model was selected for validation (first error only)
    item_type : type[BaseModel] | None
        The inferred type for this item (always provided if available)
    show_item_type : bool
        Whether to display the item type in the path (True for heterogeneous collections)
    structural_cache : dict[ErrorLocation, StructuralTuple] | None
        Optional cache for structural tuple computation
    original_data : dict[str, Any] | list[Any] | None
        Original input data for extracting feature details (optional)
    show_feature_data : bool
        Whether to display feature data with error (verbose mode)
    """
    loc = error["loc"]

    # Determine which model was selected for this error
    selected_model = None
    if metadata is not None and show_model_hint:
        models = models_in_path(loc, metadata, structural_cache)
        selected_model = models[0] if models else None

    # Filter out union markers from the path using structural analysis
    if metadata is not None:
        try:
            structural = get_or_create_structural_tuple(loc, metadata, structural_cache)
            # Filter out 'union', 'model', and 'discriminator' markers
            # Keep only 'list_index' and 'field' elements for display
            filtered_loc = [
                element
                for element, struct_type in zip(loc, structural, strict=False)
                if struct_type in ("list_index", "field")
            ]
        except (KeyError, TypeError, IndexError):
            # Fall back to original loc if structural analysis fails
            filtered_loc = list(loc)
    else:
        filtered_loc = list(loc)

    # Convert to dot-separated path
    path_str = format_path(filtered_loc)

    # Add item type annotation if requested (for heterogeneous collections)
    if show_item_type and item_type is not None:
        path_str = f"{path_str} [dim]({item_type.__name__})[/dim]"

    # Show model hint if this is the first error in a group
    if selected_model is not None:
        model_name = selected_model.__name__
        console.print(f"  [dim]Probable type:[/dim] {model_name}", style="blue")
        console.print()

    # Format the error message
    msg = error["msg"]
    input_value = error.get("input")

    ctx = error.get("ctx", {})
    if "error" in ctx:
        msg = ctx["error"]
        input_value = None

    # Skip error summary lines in verbose mode
    if not show_feature_data:
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

    # Show feature data in verbose mode
    if show_feature_data and original_data is not None:
        # Extract item index from error location
        item_index = get_item_index(loc)

        # Extract flattened feature data
        feature = extract_feature_data(original_data, item_index)

        if feature:
            # Convert filtered_loc to error path format (list of str/int)
            # Strip out the list index since we've already extracted that feature
            error_path = list(filtered_loc)
            if error_path and isinstance(error_path[0], int):
                error_path = error_path[1:]  # Remove list index

            # Select context fields
            selected_fields = select_context_fields(feature, error_path, context_size=1)

            if selected_fields:
                # Create and display panel (with item index for title)
                panel = create_feature_display(
                    selected_fields,
                    [(error_path, msg)],
                    item_index=item_index,
                )
                # Print panel directly (it has its own borders, no extra indentation needed)
                console.print(panel)
                console.print()
