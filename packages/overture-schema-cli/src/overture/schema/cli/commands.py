"""Click-based CLI for overture-schema package."""

import builtins
import io
import json
import sys
from collections import Counter, defaultdict
from functools import reduce
from operator import or_
from pathlib import Path
from typing import Annotated, Any, Literal, cast, get_args, get_origin

import click
import yaml
from pydantic import BaseModel, Field, Tag, TypeAdapter, ValidationError
from rich.console import Console
from rich.text import Text
from yamlcore import CoreLoader  # type: ignore

from overture.schema.common import OvertureFeature
from overture.schema.system.discovery import (
    ModelDict,
    ModelKey,
    TagSelector,
    discover_models,
    filter_models,
)
from overture.schema.system.discovery.tag import get_values_for_key
from overture.schema.system.feature import Feature
from overture.schema.system.json_schema import json_schema

from .error_formatting import (
    format_validation_error,
    format_validation_errors_verbose,
    group_errors_by_discriminator,
    select_most_likely_errors,
)
from .tag_options import build_selector, tag_selection_options
from .type_analysis import StructuralTuple, get_item_index, introspect_union
from .types import ErrorLocation, UnionType

# Console instances for rich output
stdout = Console(highlight=False)
stderr = Console(highlight=False, file=sys.stderr)


def _is_geojson_feature(data: dict) -> bool:
    """Check if data is in GeoJSON Feature format."""
    return data.get("type") == "Feature" and "properties" in data


def _can_discriminate(model_class: object) -> bool:
    """Check if a model can participate in a discriminated union.

    Returns True if the model is an OvertureFeature with a single literal 'type' value.
    """
    if not (isinstance(model_class, type) and issubclass(model_class, OvertureFeature)):
        return False

    return _type_literal(cast(type[OvertureFeature], model_class)) is not None


def _type_literal(feature_class: type[OvertureFeature]) -> str | None:
    """Extract the literal value from an OvertureFeature's 'type' field.

    Returns the literal type value, or None if not a single literal.
    """
    if "type" not in feature_class.model_fields:
        return None

    type_annotation = feature_class.model_fields["type"].annotation

    # Unwrap Annotated if present
    while get_origin(type_annotation) is Annotated:
        type_annotation = get_args(type_annotation)[0]

    # Check if it's a Literal with a single value
    if get_origin(type_annotation) is Literal:
        args = get_args(type_annotation)
        if len(args) == 1 and isinstance(args[0], str):
            return args[0]

    return None


def _discriminated_union(feature_classes: tuple[type[OvertureFeature], ...]) -> Any:  # noqa: ANN401
    """Create a discriminated union of Overture features on the 'type' field."""
    if not feature_classes:
        return None
    elif len(feature_classes) == 1:
        # Single model doesn't need a discriminated union
        return feature_classes[0]

    return Annotated[
        reduce(
            or_,
            (Annotated[f, Tag(cast(str, _type_literal(f)))] for f in feature_classes),
        ),
        Field(discriminator=Feature.field_discriminator("type", *feature_classes)),
    ]


def create_union_type_from_models(
    models: ModelDict,
) -> UnionType:
    """Create a union type from a dict of models.

    Uses discriminated unions for OvertureFeatures when possible for better performance.

    Args
    ----
        models: Dict mapping ModelKey to Pydantic model classes

    Returns
    -------
        Union type suitable for TypeAdapter
    """
    if not models:
        raise ValueError("No models provided")

    model_list = list(models.values())

    # Separate models that can be discriminated from those that cannot
    discriminated_models = tuple(
        cast(type[OvertureFeature], m) for m in model_list if _can_discriminate(m)
    )
    discriminated_union = _discriminated_union(discriminated_models)

    non_discriminated_models = [m for m in model_list if not _can_discriminate(m)]
    # Use None only if list is empty, otherwise build union
    non_discriminated_union = (
        reduce(or_, non_discriminated_models) if non_discriminated_models else None
    )

    # Combine discriminated and non-discriminated unions
    if discriminated_union and non_discriminated_union:
        return discriminated_union | non_discriminated_union
    elif discriminated_union:
        return discriminated_union
    elif non_discriminated_union:
        return non_discriminated_union
    else:
        raise RuntimeError("No valid models found")


def validate_feature(data: dict, model_type: UnionType) -> BaseModel:
    """Validate a single feature against the model type.

    Args
    ----
        data: Feature data to validate (GeoJSON or flat format)
        model_type: Union type for validation

    Returns
    -------
        Validated model instance

    Raises
    ------
        ValidationError: If validation fails
    """
    adapter = TypeAdapter(model_type)
    if isinstance(data, dict) and _is_geojson_feature(data):
        # Use validate_json to trigger the model's GeoJSON handling
        return cast(BaseModel, adapter.validate_json(json.dumps(data)))
    return cast(BaseModel, adapter.validate_python(data))


def validate_features(data: list, model_type: UnionType) -> list[BaseModel]:
    """Validate a list of features against the model type.

    Args
    ----
        data: List of feature data to validate (GeoJSON or flat format)
        model_type: Union type for validation

    Returns
    -------
        List of validated model instances

    Raises
    ------
        ValidationError: If validation fails
    """
    # Check if any items are GeoJSON features
    has_geojson = any(
        isinstance(item, dict) and _is_geojson_feature(item) for item in data
    )

    list_type = list[model_type]  # type: ignore[misc,valid-type]
    adapter = TypeAdapter(list_type)

    if has_geojson:
        # Use validate_json to trigger the model's GeoJSON handling
        return cast(list[BaseModel], adapter.validate_json(json.dumps(data)))
    return cast(list[BaseModel], adapter.validate_python(data))


def resolve_types(
    selector: TagSelector = TagSelector(),
    *,
    type_names: tuple[str, ...] = (),
) -> UnionType:
    """Resolve a TagSelector + type-names into a Pydantic union type."""
    models = discover_models()
    models = filter_models(models, selector, type_names=type_names)

    if not models:
        raise ValueError("No models found matching the specified criteria")

    return create_union_type_from_models(models)


def get_source_name(filename: Path) -> str:
    """Get display name for input source.

    Args
    ----
        filename: Path to input file or "-" for stdin

    Returns
    -------
        Display name: "<stdin>" for stdin input, otherwise the filename
    """
    return "<stdin>" if str(filename) == "-" else str(filename)


@click.group()
@click.version_option(package_name="overture-schema")
def cli() -> None:
    r"""Overture Schema command-line interface.

    Provides validation, schema generation, and type discovery for Overture Maps data.

    \b
    Examples:
      # Validate a file
      $ overture-schema validate data.json
    \b
      # Validate from stdin
      $ overture-schema validate - < data.json
    \b
      # List available types
      $ overture-schema list-types
    \b
      # Generate JSON schema
      $ overture-schema json-schema --tag overture:theme=buildings
    \b
      # Validate specific types
      $ overture-schema validate --tag overture:theme=buildings data.json
    """
    pass


def load_input(filename: Path) -> tuple[dict | list, str]:
    """Load and parse input from file or stdin.

    Args
    ----
        filename: Path to input file, or "-" for stdin

    Returns
    -------
        Tuple of (parsed_data, source_name)

    Raises
    ------
        yaml.YAMLError: If input is invalid YAML/JSON
        SystemExit: If filename doesn't exist or isn't a file
    """
    if str(filename) == "-":
        # Read all stdin content
        content = sys.stdin.read()

        # Try to detect JSONL format (newline-delimited JSON)
        # JSONL has multiple non-empty lines, each containing a complete JSON object
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]

        if len(lines) > 1:
            # Attempt to parse as JSONL
            try:
                parsed_lines = [json.loads(line) for line in lines]
                return parsed_lines, "<stdin>"
            except json.JSONDecodeError:
                # Not valid JSONL, fall through to YAML parser
                pass

        # Parse as single YAML/JSON document
        data = yaml.load(io.StringIO(content), Loader=CoreLoader)
        return data, "<stdin>"

    if not filename.is_file():
        raise click.UsageError(f"'{filename}' is not a file.")

    # Warn about unexpected file extensions
    if filename.suffix not in {".json", ".yaml", ".yml", ".geojson"}:
        click.echo(
            f"Warning: File '{filename}' has unexpected extension. "
            f"Expecting .json, .yaml, .yml, or .geojson",
            err=True,
        )

    # Use YAML-1.2-compliant loader (YAML-1.2 dropped support for yes/no boolean values)
    with filename.open("r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=CoreLoader)

    return data, str(filename)


def perform_validation(data: dict | list, model_type: UnionType) -> None:
    """Validate data based on its structure.

    Automatically detects and handles three input formats:
    - Single feature (dict)
    - List of features (list)
    - GeoJSON FeatureCollection (dict with type="FeatureCollection")

    Args
    ----
    data : dict | list
        Parsed data to validate
    model_type : UnionType
        Union type for validation

    Raises
    ------
    ValidationError
        If validation fails
    """
    if isinstance(data, list):
        # List of features
        validate_features(data, model_type)
    elif isinstance(data, dict) and data.get("type") == "FeatureCollection":
        # GeoJSON FeatureCollection
        validate_features(data["features"], model_type)
    else:
        # Single feature
        validate_feature(data, model_type)


def compute_collection_statistics(
    item_types: dict[int, builtins.type[BaseModel] | None],
    filtered_errors: list,
) -> tuple[
    int,
    Counter[builtins.type[BaseModel] | None],
    dict[builtins.type[BaseModel], set[int]],
]:
    """Compute validation statistics for heterogeneous collections.

    Args
    ----
    item_types : dict[int, type[BaseModel] | None]
        Mapping from item index to detected model type
    filtered_errors : list
        List of filtered validation errors

    Returns
    -------
    tuple
        Tuple of (items_without_errors, type_counts, items_with_errors_by_type)
    """
    # Compute statistics: group items by type
    type_counts: Counter[builtins.type[BaseModel] | None] = Counter(item_types.values())

    # Determine total number of items (max index + 1, or count from data)
    max_index = max(item_types.keys()) if item_types else -1
    total_items = max_index + 1

    # Count items with errors per type
    items_with_errors_by_type: dict[builtins.type[BaseModel], set[int]] = {}
    for err in filtered_errors:
        idx = get_item_index(err["loc"])
        if idx is not None and idx in item_types:
            model_type_cls = item_types[idx]
            if model_type_cls is not None:
                if model_type_cls not in items_with_errors_by_type:
                    items_with_errors_by_type[model_type_cls] = set()
                items_with_errors_by_type[model_type_cls].add(idx)

    # Count items without any errors
    items_without_errors = total_items - len(
        {
            idx
            for idx in item_types.keys()
            if any(get_item_index(err["loc"]) == idx for err in filtered_errors)
        }
    )

    return items_without_errors, type_counts, items_with_errors_by_type


def print_collection_statistics(
    items_without_errors: int,
    type_counts: Counter[builtins.type[BaseModel] | None],
    items_with_errors_by_type: dict[builtins.type[BaseModel], set[int]],
    stderr: Console,
) -> None:
    """Print validation statistics for heterogeneous collections.

    Args
    ----
    items_without_errors : int
        Count of items with no validation errors
    type_counts : Counter[type[BaseModel] | None]
        Counter of items by model type
    items_with_errors_by_type : dict[type[BaseModel], set[int]]
        Mapping from model type to set of item indices with errors
    stderr : Console
        Console for stderr output
    """
    stderr.print("  [dim]Collection statistics:[/dim]")

    # Show items without errors first
    # TODO: Once we switch to parse_features (instead of validate_features),
    # we can include type information for items without errors by parsing
    # the input and tracking which items validated successfully and their types.
    # This would allow output like: "Building: 2 confirmed (no errors)"
    if items_without_errors > 0:
        stderr.print(
            f"    • {items_without_errors} item{'s' if items_without_errors != 1 else ''} with no errors",
            style="dim",
        )

    # Show per-type statistics
    for model_type_cls, count in type_counts.most_common():
        if model_type_cls is not None:
            items_with_errors = len(
                items_with_errors_by_type.get(model_type_cls, set())
            )
            valid_count = count - items_with_errors

            if valid_count > 0:
                stderr.print(
                    f"    • {model_type_cls.__name__}: {valid_count} confirmed, {items_with_errors} with errors",
                    style="dim",
                )
            else:
                stderr.print(
                    f"    • {model_type_cls.__name__} (probable): {items_with_errors} item{'s' if items_with_errors != 1 else ''} with errors",
                    style="dim",
                )
    stderr.print()


def handle_validation_error(
    e: ValidationError,
    model_type: UnionType,
    stderr: Console,
    original_data: dict | list | None = None,
    show_fields: list[str] | None = None,
) -> None:
    """Handle and format validation errors with rich contextual information.

    Groups errors by discriminator, selects most likely error groups, and provides
    helpful diagnostics for heterogeneous collections and ambiguous types.

    Args
    ----
    e : ValidationError
        ValidationError from pydantic
    model_type : UnionType
        Union type used for validation
    stderr : Console
        Console for stderr output
    original_data : dict | list | None
        Original input data for error display
    show_fields : list[str] | None
        List of field names to display alongside errors
    """
    # Compute metadata once upfront
    metadata = introspect_union(model_type)

    # Create cache for structural tuple computation (optimizes systematic errors)
    structural_cache: dict[ErrorLocation, StructuralTuple] = {}

    # Group errors by discriminator path and select most likely group(s)
    error_groups = group_errors_by_discriminator(e.errors(), metadata, structural_cache)
    filtered_errors, is_tied, is_heterogeneous, item_types = select_most_likely_errors(
        error_groups,
        metadata=metadata,
        all_errors=e.errors(),
        structural_cache=structural_cache,
    )

    # Show heterogeneity warning if collection has mixed types
    if is_heterogeneous:
        stderr.print(
            "  ⚠ Heterogeneous collection: Data contains multiple feature types. Consider:",
            style="yellow",
        )
        stderr.print(
            "    • Validating each type separately with --tag, --filter, "
            "--exclude, or --type",
            style="dim",
        )
        stderr.print()

        # Compute and display statistics if there are errors to report
        if filtered_errors:
            items_without_errors, type_counts, items_with_errors_by_type = (
                compute_collection_statistics(item_types, filtered_errors)
            )
            print_collection_statistics(
                items_without_errors, type_counts, items_with_errors_by_type, stderr
            )

    # Show tie indicator if multiple groups had same error count
    elif is_tied:
        stderr.print(
            "  ⚠ Ambiguous: Data matches multiple types equally. Consider:",
            style="yellow",
        )
        stderr.print(
            "    • Specifying --tag or --type to narrow validation", style="dim"
        )
        stderr.print("    • Adding discriminator fields to clarify intent", style="dim")
        stderr.print()

    # Group errors by item

    errors_by_item: dict[int | None, list] = defaultdict(list)
    for error in filtered_errors:
        item_idx = get_item_index(error["loc"])
        errors_by_item[item_idx].append(error)

    # Display errors grouped by item

    for item_idx, item_errors in errors_by_item.items():
        # Determine item type
        error_item_type = None
        if item_idx is not None and item_idx in item_types:
            error_item_type = item_types.get(item_idx)

        # Try verbose display first
        displayed = format_validation_errors_verbose(
            item_errors,
            stderr,
            metadata=metadata,
            item_type=error_item_type,
            structural_cache=structural_cache,
            original_data=original_data,
            item_index=item_idx,
            show_fields=show_fields,
        )

        # Fall back to non-verbose format if verbose couldn't display
        if not displayed:
            for i, error in enumerate(item_errors):
                format_validation_error(
                    error,
                    stderr,
                    metadata=metadata,
                    show_model_hint=(i == 0),
                    item_type=error_item_type,
                    show_item_type=is_heterogeneous,
                    structural_cache=structural_cache,
                    original_data=original_data,
                    show_feature_data=False,
                )


def handle_generic_error(e: Exception, filename: Path, error_type: str) -> None:
    """Handle generic errors during validation.

    Args
    ----
    e : Exception
        Exception that occurred
    filename : Path
        Input filename or "-" for stdin
    error_type : str
        Type of error for user-friendly message

    Raises
    ------
    click.UsageError
        Always, with formatted error message
    """
    source_name = get_source_name(filename)

    if error_type == "yaml":
        raise click.UsageError(f"'{source_name}' contains invalid input: {e}")
    elif error_type == "value":
        raise click.UsageError(str(e))
    elif error_type == "key":
        raise click.UsageError(f"Invalid data structure - missing key: {e}")
    else:
        raise click.UsageError(f"Error processing {source_name}: {e}")


@cli.command()
@click.argument("filename", type=click.Path(path_type=Path), required=True)
@tag_selection_options
@click.option(
    "--type",
    "types",
    multiple=True,
    help="Specific type to validate against (e.g., building, segment)",
)
@click.option(
    "--show-field",
    "show_fields",
    multiple=True,
    help="Field to display alongside errors (e.g., id, version). Can be repeated.",
)
def validate(
    filename: Path,
    tags: tuple[str, ...],
    filters: tuple[str, ...],
    excludes: tuple[str, ...],
    types: tuple[str, ...],
    show_fields: tuple[str, ...],
) -> None:
    r"""Validate Overture Maps data against schemas.

    Read from FILENAME or stdin if FILENAME is '-'.
    Supports JSON, YAML, and GeoJSON formats.

    \b
    Examples:
      # Validate a file
      $ overture-schema validate data.json
    \b
      # Validate from stdin
      $ overture-schema validate - < data.json
    \b
      # Validate only buildings
      $ overture-schema validate --tag overture:theme=buildings data.json
    \b
      # Validate specific type
      $ overture-schema validate --type building data.json
    \b
      # Official Overture types only
      $ overture-schema validate --tag overture --tag feature data.json
    """
    # Resolve model type first (errors here are ValueErrors, not ValidationErrors)
    try:
        model_type = resolve_types(
            build_selector(tags, filters, excludes), type_names=types
        )
    except ValueError as e:
        handle_generic_error(e, filename, "value")
        return

    # Load input (errors here are YAMLErrors or ValueErrors, not ValidationErrors)
    try:
        data, source_name = load_input(filename)
    except yaml.YAMLError as e:
        handle_generic_error(e, filename, "yaml")
        return
    except KeyError as e:
        handle_generic_error(e, filename, "key")
        return

    # Perform validation (now model_type and data are guaranteed to be defined)
    try:
        perform_validation(data, model_type)
        stdout.print(f"✓ Successfully validated {source_name}")
    except ValidationError as e:
        handle_validation_error(
            e, model_type, stderr, original_data=data, show_fields=list(show_fields)
        )
        sys.exit(1)


@cli.command("json-schema")
@tag_selection_options
@click.option(
    "--type",
    "types",
    multiple=True,
    help="Specific type to generate schema for (e.g., building, segment)",
)
def json_schema_command(
    tags: tuple[str, ...],
    filters: tuple[str, ...],
    excludes: tuple[str, ...],
    types: tuple[str, ...],
) -> None:
    r"""Generate JSON schema for Overture Maps types.

    Outputs a JSON Schema document to stdout that can be used for validation
    or documentation purposes.

    \b
    Examples:
      # All types
      $ overture-schema json-schema > schema.json
    \b
      # Buildings theme by tag
      $ overture-schema json-schema --tag overture:theme=buildings
    \b
      # Specific types
      $ overture-schema json-schema --type building
    \b
      # Official Overture types only
      $ overture-schema json-schema --tag overture --tag feature
    """
    try:
        model_type = resolve_types(
            build_selector(tags, filters, excludes), type_names=types
        )
        schema = json_schema(model_type)
        # Use plain print for JSON output to avoid Rich formatting
        print(json.dumps(schema, indent=2, sort_keys=True))
    except ValueError as e:
        raise click.UsageError(str(e)) from e


@cli.command("list-types")
@tag_selection_options
@click.option(
    "--group-by",
    help="Group types by a key/value tag's key (e.g. 'overture:theme'). "
    "Plain and namespaced tags have no value to group by and are "
    "ignored here.",
)
def list_types(
    tags: tuple[str, ...],
    filters: tuple[str, ...],
    excludes: tuple[str, ...],
    group_by: str | None,
) -> None:
    r"""List all available types.

    Displays all registered models and can be organized by grouping.

    \b
    Examples:
      # List all types
      $ overture-schema list-types
    """
    try:
        models = discover_models()
        models = filter_models(models, build_selector(tags, filters, excludes))

        if group_by:
            grouped_models: dict[str, set[ModelKey]] = {}

            for key in models.keys():
                if groups := get_values_for_key(key.tags, group_by):
                    for group in groups:
                        grouped_models.setdefault(group, set()).add(key)

            padding = (
                max(
                    (len(key.name) for keys in grouped_models.values() for key in keys),
                    default=0,
                )
                + 2
            )

            for group, keys in sorted(grouped_models.items()):
                stdout.print(
                    f"[green bold]{group_by}={group} ({len(keys)})[/green bold]"
                )
                for key in sorted(keys, key=lambda k: k.name):
                    model = Text()
                    model.append("→ ", style="bright_black")
                    model.append(key.name, style="bold cyan")
                    model.pad_right(max(1, padding - len(key.name)))
                    model.append("  ".join(sorted(key.tags)))
                    stdout.print(model)
                stdout.print()

        else:
            padding = max((len(key.name) for key in models.keys()), default=0) + 2

            for key in sorted(models.keys(), key=lambda k: k.name):
                model = Text()
                model.append(key.name, style="bold cyan")
                model.pad_right(max(1, padding - len(key.name)))
                model.append("  ".join(sorted(key.tags)))
                stdout.print(model)

    except Exception as e:
        click.echo(f"Error listing types: {e}", err=True)


if __name__ == "__main__":
    cli()
