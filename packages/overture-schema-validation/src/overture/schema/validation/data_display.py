"""Data display utilities for verbose error output."""

from typing import Any

from rich.panel import Panel
from rich.table import Table

# Display configuration constants
DEFAULT_FIELD_VALUE_MAX_LENGTH = 50
DEFAULT_CONTEXT_SIZE = 1


def _format_nested_path(error_path: list[str | int]) -> str:
    """Format error path as displayable nested key.

    Converts paths like ["sources", 0, "confidence"] into "sources[0].confidence".

    Args
    ----
        error_path: List of field names (str) and array indices (int)

    Returns
    -------
        Formatted path string with dots and brackets
    """
    parts: list[str] = []
    for element in error_path:
        if isinstance(element, str):
            # Add dot separator before field names (except first, and not right after opening)
            if parts and not parts[-1].endswith("]"):
                parts.append(".")
            elif parts and parts[-1].endswith("]"):
                # Add dot after array index before field name
                parts.append(".")
            parts.append(element)
        elif isinstance(element, int):
            # Add array index in brackets
            parts.append(f"[{element}]")
    return "".join(parts)


def _has_nested_context(error_path: list[str | int]) -> bool:
    """Check if error path represents nested context.

    Returns True if the path has multiple fields or contains array indices.

    Args
    ----
        error_path: Path to error field

    Returns
    -------
        True if path is nested (multiple fields or has array index)
    """
    string_elements = sum(1 for e in error_path if isinstance(e, str))
    has_array_index = any(isinstance(e, int) for e in error_path)
    return string_elements > 1 or has_array_index


def extract_feature_data(
    data: dict[str, Any] | list[Any] | Any,  # noqa: ANN401
    item_index: int | None,
) -> dict[str, Any]:
    """Extract and flatten a feature from various input formats.

    Handles single features, lists of features, and GeoJSON FeatureCollections.
    Flattens GeoJSON format (properties nested under 'properties' key) to
    flat format (properties at top level).

    Args
    ----
        data: Input data (dict, list, or FeatureCollection)
        item_index: Index of item in list/collection, or None for single feature

    Returns
    -------
        Flattened feature dict, or empty dict if extraction fails
    """
    try:
        # Handle list of features
        if isinstance(data, list):
            if item_index is None or item_index < 0 or item_index >= len(data):
                return {}
            feature = data[item_index]
        # Handle FeatureCollection
        elif isinstance(data, dict) and data.get("type") == "FeatureCollection":
            features = data.get("features", [])
            if item_index is None or item_index < 0 or item_index >= len(features):
                return {}
            feature = features[item_index]
        # Handle single feature
        elif isinstance(data, dict):
            feature = data
        else:
            return {}

        # Flatten properties if in GeoJSON format
        if isinstance(feature, dict) and "properties" in feature:
            # Start with top-level fields (id, geometry, etc.)
            flattened = {}
            if "id" in feature:
                flattened["id"] = feature["id"]
            if "geometry" in feature:
                flattened["geometry"] = feature["geometry"]

            # Add properties at top level
            properties = feature.get("properties", {})
            if isinstance(properties, dict):
                flattened.update(properties)

            return flattened
        elif isinstance(feature, dict):
            # Already flat format
            return feature
        else:
            return {}

    except (TypeError, KeyError, AttributeError):
        # Handle malformed or unexpected data structures gracefully
        return {}


def _select_context_for_array_index_error(
    feature: dict[str, Any],
    error_path: list[str | int],
    context_size: int,
) -> dict[str, Any]:
    """Handle error paths where the target is an array index.

    When the error path ends with an array index (e.g., ["data_download_url", 0]),
    we can't select "sibling fields" because array items don't have siblings.
    Instead, show the parent array field with context.

    Args
    ----
        feature: Flattened feature dict
        error_path: Path ending with an array index
        context_size: Number of neighboring fields to include

    Returns
    -------
        Dict of selected fields showing context around the array
    """
    # Find the path up to the last string field (the array field itself)
    array_field_path: list[str | int] = []
    for element in error_path:
        array_field_path.append(element)
        if isinstance(element, str):
            # Keep going until we hit an int, but remember the last string position
            pass

    # Find the last string element's index
    last_string_idx = -1
    for i, element in enumerate(error_path):
        if isinstance(element, str):
            last_string_idx = i

    if last_string_idx < 0:
        # No string elements at all - return empty
        return {}

    # Truncate path to end at the array field (last string element)
    array_path = list(error_path[: last_string_idx + 1])

    # Navigate to get the array value
    current: Any = feature
    for element in array_path[:-1]:  # Navigate to parent of array field
        if isinstance(current, dict) and isinstance(element, str):
            current = current.get(element, {})
        elif isinstance(current, list) and isinstance(element, int):
            if 0 <= element < len(current):
                current = current[element]
            else:
                return {}

    # Now current should be the dict containing the array field
    array_field_name = array_path[-1]
    if not isinstance(array_field_name, str):
        return {}

    # Build the display with nested path notation
    selected: dict[str, Any] = {}

    # Format the full path including the array index
    full_path_str = _format_nested_path(error_path)

    if isinstance(current, dict):
        # Get array value and the specific item
        array_value = current.get(array_field_name)

        # Find the array index in the error path
        array_indices = [
            e for e in error_path[last_string_idx + 1 :] if isinstance(e, int)
        ]
        if array_indices and isinstance(array_value, list):
            idx = array_indices[0]
            if 0 <= idx < len(array_value):
                # Show the specific array item
                selected[full_path_str] = array_value[idx]
            else:
                selected[full_path_str] = None
        else:
            # Show the whole array
            selected[full_path_str] = array_value

        # Add context fields from the parent dict
        if len(array_path) > 1:
            # Navigate to parent to get sibling fields
            parent_path = array_path[:-1]
            prefix = _format_nested_path(parent_path)
            parent_fields = list(current.keys())

            if array_field_name in parent_fields:
                target_idx = parent_fields.index(array_field_name)
                start = max(0, target_idx - context_size)
                end = min(len(parent_fields), target_idx + context_size + 1)

                for i in range(start, end):
                    field = parent_fields[i]
                    if field != array_field_name:
                        key = f"{prefix}.{field}" if prefix else field
                        selected[key] = current.get(field)
    else:
        # Fallback: just show the path
        selected[full_path_str] = None

    return selected


def select_context_fields(
    feature: dict[str, Any],
    error_path: list[str | int],
    context_size: int = DEFAULT_CONTEXT_SIZE,
    pinned_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Select relevant fields for display around an error location.

    Selects the error field plus neighboring fields for context. For nested
    error paths (e.g., ["geometry", "type"] or ["sources", 0, "confidence"]),
    navigates into the structure and selects the specific nested value.

    Args
    ----
        feature: Flattened feature dict
        error_path: Path to error field (may include array indices)
        context_size: Number of neighboring fields to include on each side
        pinned_fields: List of field names to always include (even outside context window)

    Returns
    -------
        Dict of selected fields with their values
    """
    if not error_path:
        return {}

    # Navigate to the value at error_path
    # Special case: don't navigate into geometry (it's treated as opaque)
    current: Any = feature  # Type can change as we navigate through nested structures
    navigated_path = []
    successfully_navigated = True

    for i, element in enumerate(error_path):
        navigated_path.append(element)

        # Stop navigation if we encounter 'geometry' as a field name
        if isinstance(element, str) and element == "geometry":
            # Include geometry but don't navigate deeper
            if isinstance(current, dict) and element in current:
                current = current[element]
            # Check if there are more elements after geometry
            if i + 1 < len(error_path):
                successfully_navigated = False
            break

        if isinstance(current, dict) and isinstance(element, str):
            if element in current:
                current = current[element]
            else:
                # Field doesn't exist - mark as None and stop navigating
                current = None
                successfully_navigated = False
                break
        elif isinstance(current, list) and isinstance(element, int):
            if 0 <= element < len(current):
                current = current[element]
            else:
                # Index out of range
                current = None
                successfully_navigated = False
                break
        else:
            # Can't navigate further (e.g., trying to access a field on a non-dict)
            # Keep current at the last successful level
            successfully_navigated = False
            break

    # Determine if we're dealing with a nested path (has array index or multiple fields)
    has_nested = _has_nested_context(error_path)

    # If path contains an array index, include the entire array at top level
    has_array_index = any(isinstance(e, int) for e in error_path)

    # Initialize selected fields dict (populated in different branches below)
    selected: dict[str, Any] = {}

    # Check if navigation failed only on the last element (missing field case)
    # In this case, we should still generate nested paths
    navigation_failed_on_last = (
        not successfully_navigated
        and len(navigated_path) == len(error_path)
        and current is None
    )

    if has_nested and (successfully_navigated or navigation_failed_on_last):
        # For nested paths like ["sources", 0, "confidence"], show:
        # 1. Top-level context around the parent field (e.g., fields around "sources")
        # 2. Nested context within the parent object (e.g., fields around "confidence" in sources[0])

        parent_path = error_path[:-1]  # All but the last element
        target_field = error_path[-1]  # Last element (e.g., "confidence")

        if not isinstance(target_field, str):
            # Last element is an array index - show context around the parent array
            # Navigate to find the deepest string field to use as context
            return _select_context_for_array_index_error(
                feature, error_path, context_size
            )

        # Get top-level field name (first string in path)
        top_level_field = None
        for element in error_path:
            if isinstance(element, str):
                top_level_field = element
                break

        if not top_level_field:
            return {}

        # First, add top-level context (fields around the parent field)
        field_names = list(feature.keys())
        if top_level_field in field_names:
            target_index = field_names.index(top_level_field)
        else:
            field_names.append(top_level_field)
            target_index = len(field_names) - 1

        start_index = max(0, target_index - context_size)
        end_index = min(len(field_names), target_index + context_size + 1)

        # Add top-level elision marker if needed
        if start_index > 0 and context_size > 0:
            selected["..."] = "..."

        # Add top-level context fields (but not the nested field itself, we'll add that with nested keys)
        for i in range(start_index, end_index):
            field_name = field_names[i]
            if field_name != top_level_field:
                selected[field_name] = feature.get(field_name)

        # Add top-level elision marker at end if needed
        if end_index < len(field_names) and context_size > 0:
            selected["... "] = "..."

        # Now navigate to parent and add nested context
        parent: Any = feature  # Type changes as we navigate through nested structures
        for element in parent_path:
            if isinstance(parent, dict) and isinstance(element, str):
                parent = parent.get(element)
            elif isinstance(parent, list) and isinstance(element, int):
                if 0 <= element < len(parent):
                    parent = parent[element]
                else:
                    return selected
            else:
                return selected

        # Apply context selection within the parent object
        if not isinstance(parent, dict):
            return selected

        parent_fields = list(parent.keys())
        if target_field in parent_fields:
            nested_target_index = parent_fields.index(target_field)
        else:
            parent_fields.append(target_field)
            nested_target_index = len(parent_fields) - 1

        nested_start = max(0, nested_target_index - context_size)
        nested_end = min(len(parent_fields), nested_target_index + context_size + 1)

        # Build path prefix once for reuse (without trailing dot)
        prefix_str = _format_nested_path(parent_path)

        # Add nested elision marker at start if needed
        if nested_start > 0 and context_size > 0:
            selected[f"{prefix_str}...."] = (
                "..."  # Dot + "..." for nested elision: sources[0]....
            )

        # Add nested fields with full paths
        for i in range(nested_start, nested_end):
            field_name = parent_fields[i]
            full_key = f"{prefix_str}.{field_name}"
            selected[full_key] = parent.get(field_name)  # parent is verified dict above

        # Add nested elision marker at end if needed
        if nested_end < len(parent_fields) and context_size > 0:
            selected[f"{prefix_str}.... "] = (
                "..."  # Space differentiates from start marker
            )

        return selected

    # Get the top-level field name (first string element)
    top_level_field = None
    for element in error_path:
        if isinstance(element, str):
            top_level_field = element
            break

    if top_level_field is None:
        return {}

    # Get all field names in order
    field_names = list(feature.keys())

    # Find the target field
    if top_level_field in field_names:
        target_index = field_names.index(top_level_field)
    else:
        # Field is missing - still include it with None
        field_names.append(top_level_field)
        target_index = len(field_names) - 1

    # Select fields within context window
    start_index = max(0, target_index - context_size)
    end_index = min(len(field_names), target_index + context_size + 1)

    # Add "..." marker if fields were elided at the start (only if context_size > 0)
    if start_index > 0 and context_size > 0:
        selected["..."] = "..."

    for i in range(start_index, end_index):
        field_name = field_names[i]
        if field_name in feature:
            # For the error field with nested path, check if we should show the whole field or navigate
            if field_name == top_level_field and len(error_path) > 1:
                # If path has array index, include entire array/field
                if has_array_index:
                    selected[field_name] = feature[field_name]
                # Special case: if field is 'geometry', just show it without nested path
                # since geometry is opaque
                elif field_name == "geometry":
                    selected[field_name] = current
                else:
                    # Build nested key with array indices: ["sources", 0, "confidence"] -> "sources[0].confidence"
                    nested_key = _format_nested_path(error_path)
                    selected[nested_key] = current
            else:
                selected[field_name] = feature[field_name]
        else:
            # Missing field - include with None
            selected[field_name] = None

    # Add "..." marker if fields were elided at the end (only if context_size > 0)
    if end_index < len(field_names) and context_size > 0:
        selected["... "] = (
            "..."  # Use "... " (with space) to distinguish from start marker
        )

    # Add pinned fields that aren't already in selected
    # We need to maintain field order, so rebuild the dict
    if pinned_fields:
        # Build ordered dict with all fields (selected + pinned) in natural order
        ordered_selected: dict[str, Any] = {}

        # Add start elision marker
        if "..." in selected:
            ordered_selected["..."] = selected["..."]

        # Add all fields in feature order (including pinned fields)
        for field_name in field_names:
            # Include if already selected OR if it's a pinned field
            if field_name in selected:
                ordered_selected[field_name] = selected[field_name]
            elif field_name in pinned_fields:
                ordered_selected[field_name] = feature.get(field_name)

        # Add pinned fields that don't exist in the feature (at end with None)
        for pinned_field in pinned_fields:
            if pinned_field not in field_names and pinned_field not in ordered_selected:
                ordered_selected[pinned_field] = None

        # Add end elision marker
        if "... " in selected:
            ordered_selected["... "] = selected["... "]

        return ordered_selected

    return selected


def format_field_value(
    value: object,
    max_length: int = DEFAULT_FIELD_VALUE_MAX_LENGTH,
) -> str:
    """Format a field value for display.

    Args
    ----
        value: Field value to format
        max_length: Maximum length before truncation

    Returns
    -------
        Formatted string representation
    """
    # Handle None (missing fields)
    if value is None:
        return "<missing>"

    # Handle empty collections
    if value == []:
        return "[]"
    if value == {}:
        return "{}"

    # Handle geometry objects
    if isinstance(value, dict) and "type" in value:
        geom_type = value.get("type")
        if geom_type in {
            "Point",
            "LineString",
            "Polygon",
            "MultiPoint",
            "MultiLineString",
            "MultiPolygon",
            "GeometryCollection",
        }:
            return str(geom_type)

    # Handle nested objects - extract key info
    if isinstance(value, dict):
        # Try to extract primary field
        if "primary" in value:
            primary = value["primary"]
            # Quote strings in nested display
            if isinstance(primary, str):
                return f'primary: "{primary}"'
            return f"primary: {primary}"
        # Otherwise show first few keys
        keys = list(value.keys())[:3]
        return "{" + ", ".join(f"{k}: ..." for k in keys) + "}"

    # Handle arrays
    if isinstance(value, list):
        return f"[...{len(value)} items]"

    # Handle strings - add quotes
    if isinstance(value, str):
        result = f'"{value}"'
        # Truncate if too long (accounting for quotes)
        if len(result) > max_length + 2:
            return '"' + value[:max_length] + '..."'
        return result

    # Handle other primitives
    result = str(value)

    # Truncate if too long
    if len(result) > max_length:
        return result[:max_length] + "..."

    return result


def create_feature_display(
    fields: dict[str, Any],
    errors: list[tuple[list[str | int], str]],
    item_index: int | None = None,
    item_type: str | None = None,
    show_fields: list[str] | None = None,
    feature: dict[str, Any] | None = None,
) -> Panel:
    """Create a Rich Panel with table displaying feature fields with error annotations.

    Creates a borderless table with four columns: field names, values, arrows, and errors,
    wrapped in a Panel with rounded borders. All error fields are annotated with
    arrows and error messages, and highlighted in bright red.

    Args
    ----
        fields: Dict of field names to values (in desired display order)
        errors: List of (error_path, error_msg) tuples for all errors in this feature
        item_index: Optional index of item in collection (for panel title)
        item_type: Optional type name to display in panel title (e.g., "Building")
        show_fields: List of field names to display in header
        feature: Full feature dict for extracting show_fields values

    Returns
    -------
        Rich Panel containing the table, ready to print
    """
    # Create table without borders (for alignment only)
    table = Table(show_header=False, show_edge=False, box=None, padding=(0, 0, 0, 1))

    # Add columns: Field (right-aligned) | Value (right-aligned) | Arrow | Error message
    table.add_column("Field", no_wrap=True, justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Arrow", no_wrap=True)  # Single arrow column
    table.add_column("Error")

    # Build mapping from field display name to error messages
    error_map: dict[str, list[str]] = {}
    for error_path, error_msg in errors:
        # Determine which field has the error (use first string in path)
        error_field: str | None = None
        for element in error_path:
            if isinstance(element, str):
                error_field = element
                break

        # Skip if no field name found (shouldn't happen in practice)
        if error_field is None:
            continue

        # Format nested path for display
        if len(error_path) > 1:
            # Special case: geometry is opaque, don't show nested path
            if error_field == "geometry":
                error_field_display = "geometry"
            else:
                # Handle nested paths like ["sources", 0, "confidence"] -> "sources[0].confidence"
                error_field_display = _format_nested_path(error_path)
        else:
            error_field_display = error_field

        # Add to error map
        if error_field_display not in error_map:
            error_map[error_field_display] = []
        error_map[error_field_display].append(error_msg)

    # Add rows for each field
    for field_name, field_value in fields.items():
        # Check if this is an elision marker (handles both simple "..." and nested "sources[0]...")
        is_elision = field_value == "..." and ("..." in field_name)

        if is_elision:
            # Display dimmed field name with blank value (4 columns now)
            table.add_row(f"[dim]{field_name}[/dim]", "", "", "")
            continue

        formatted_value = format_field_value(field_value)

        # Check if this field has errors
        if field_name in error_map:
            # Add error annotation with arrow in separate column
            field_name_styled = f"[bold bright_yellow]{field_name}[/bold bright_yellow]"
            value_styled = f"[bright_red]{formatted_value}[/bright_red]"
            # Join multiple error messages with newlines (without arrows)
            error_messages = error_map[field_name]
            error_text = "\n".join(f"[blue]{msg}[/blue]" for msg in error_messages)
            # Arrow goes in its own column
            arrow = "[cyan]←[/cyan]"
            table.add_row(field_name_styled, value_styled, arrow, error_text)
        else:
            # Apply cyan style to non-error fields, dim the value for context
            field_name_styled = f"[cyan]{field_name}[/cyan]"
            value_styled = f"[dim]{formatted_value}[/dim]"
            table.add_row(field_name_styled, value_styled, "", "")

    # Wrap table in a Panel with rounded borders
    from rich import box

    # Add title: "Validation Failed" for single features, or item info for collections
    if item_index is not None:
        if item_type:
            title = f"[{item_index}] ({item_type})"
        else:
            title = f"[{item_index}]"
    else:
        title = "[bright_red]Validation Failed[/bright_red]"

    # Add show_fields to title if provided
    if show_fields and feature:
        field_parts = []
        max_field_length = 30  # Truncate long values in header
        for field_name in show_fields:
            field_value = feature.get(field_name)
            if field_value is None:
                formatted = "<missing>"
            elif isinstance(field_value, str):
                # Truncate long strings
                if len(field_value) > max_field_length:
                    formatted = field_value[:max_field_length] + "..."
                else:
                    formatted = field_value
            else:
                # For non-strings, convert to string and truncate
                str_value = str(field_value)
                if len(str_value) > max_field_length:
                    formatted = str_value[:max_field_length] + "..."
                else:
                    formatted = str_value
            field_parts.append(f"{field_name}={formatted}")

        if field_parts:
            title = f"{title} {' '.join(field_parts)}"

    return Panel(
        table,
        box=box.HORIZONTALS,
        border_style="bright_black",
        expand=True,
        title=title,
        title_align="left",
    )
