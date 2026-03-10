"""Click-based CLI for overture-schema package."""

import json
import sys
from collections import defaultdict
from importlib.metadata import entry_points

import click
from pydantic import BaseModel
from rich.console import Console

from overture.schema.core.discovery import ModelKey, discover_models, resolve_types
from overture.schema.system.json_schema import json_schema

from .docstrings import get_model_docstring, get_theme_module_docstring
from .output import rewrap

stdout = Console(highlight=False)
stderr = Console(highlight=False, file=sys.stderr)


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
      $ overture-schema json-schema --theme buildings
    \b
      # Validate specific types
      $ overture-schema validate --theme buildings data.json
    """
    pass


def load_plugins(group: click.Group) -> None:
    """Load plugin subcommands from entry points.

    Iterates the ``overture.schema.cli`` entry point group. Each entry point
    should resolve to a ``click.Command`` or ``click.Group``. Broken plugins
    emit a warning to stderr and are skipped. Names that collide with
    already-registered commands are skipped.
    """
    for ep in entry_points(group="overture.schema.cli"):
        if ep.name in group.commands:
            continue
        try:
            cmd = ep.load()
            group.add_command(cmd, ep.name)
        except Exception as e:
            click.echo(f"Warning: failed to load plugin '{ep.name}': {e}", err=True)


@cli.command("json-schema")
@click.option(
    "--overture-types",
    is_flag=True,
    help="Generate schema for all official Overture types (excludes extensions)",
)
@click.option(
    "--namespace",
    help="Namespace to filter by (e.g., overture, annex)",
)
@click.option(
    "--theme",
    multiple=True,
    help="Theme to generate schema for (shorthand for all types in theme)",
)
@click.option(
    "--type",
    "types",
    multiple=True,
    help="Specific type to generate schema for (e.g., building, segment)",
)
def json_schema_command(
    overture_types: bool,
    namespace: str | None,
    theme: tuple[str, ...],
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
      # Buildings theme
      $ overture-schema json-schema --theme buildings
    \b
      # Specific types
      $ overture-schema json-schema --type building
    \b
      # Official Overture types only
      $ overture-schema json-schema --overture-types
    """
    try:
        effective_namespace = "overture" if overture_types else namespace
        model_type = resolve_types(effective_namespace, theme, types)
        schema = json_schema(model_type)
        # Use plain print for JSON output to avoid Rich formatting
        print(json.dumps(schema, indent=2, sort_keys=True))
    except ValueError as e:
        raise click.UsageError(str(e)) from e


def dump_namespace(
    theme_types: dict[str | None, list[tuple[ModelKey, type[BaseModel]]]],
) -> None:
    """Print all themes and types for a namespace.

    Displays themes in alphabetical order with their types and docstrings.
    Each type includes its model class name and description.

    Args
    ----
    theme_types : dict[str | None, list[tuple[ModelKey, type[BaseModel]]]]
        Dict mapping theme name to list of (ModelKey, model_class) tuples
    """
    for theme in sorted(theme_types.keys(), key=lambda x: (x is None, x)):
        if theme:
            stdout.print(
                f"[bold green underline]{theme.upper()}[/bold green underline]"
            )

            theme_docstring = get_theme_module_docstring(theme)
            if theme_docstring:
                stdout.print(
                    rewrap(theme_docstring, stdout, padding_right=4), style="dim"
                )

            stdout.print()

        sorted_types = sorted(theme_types[theme], key=lambda x: x[0].type)
        for key, model_class in sorted_types:
            stdout.print(
                f"  [bright_black]→[/bright_black] [bold cyan]{key.type}[/bold cyan] [dim magenta]({key.class_name})[/dim magenta]"
            )
            docstring = get_model_docstring(model_class)
            if docstring:
                stdout.print(
                    rewrap(docstring, stdout, indent=4, padding_right=12), style="dim"
                )
            stdout.print()


@cli.command("list-types")
def list_types() -> None:
    r"""List all available types grouped by theme with descriptions.

    Displays all registered Overture Maps types organized by theme,
    including model class names and docstrings.

    \b
    Examples:
      # List all types
      $ overture-schema list-types
    """
    models = discover_models()

    # Group models by namespace and theme
    namespaces: dict[str, dict[str | None, list[tuple[ModelKey, type[BaseModel]]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    for key, model_class in models.items():
        namespaces[key.namespace][key.theme].append((key, model_class))

    # Display Overture themes first
    if "overture" in namespaces:
        stdout.print("[bold red]OVERTURE THEMES[/bold red]", justify="center")
        stdout.print()

        dump_namespace(namespaces["overture"])

        stdout.print("[bold red]ADDITIONAL TYPES[/bold red]", justify="center")
        stdout.print()

    for namespace in sorted(namespaces.keys()):
        if namespace == "overture":
            continue

        stdout.print(f"[bold blue]{namespace.upper()}[/bold blue]")
        dump_namespace(namespaces[namespace])


# Load plugin subcommands from entry points.
# Built-in commands are already registered via @cli.command() decorators above,
# so load_plugins skips names that collide with built-ins.
load_plugins(cli)


if __name__ == "__main__":
    cli()
