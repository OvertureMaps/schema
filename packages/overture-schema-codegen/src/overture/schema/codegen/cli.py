"""CLI entrypoint for schema code generation."""

import json
import logging
from pathlib import Path, PurePosixPath

import click

from overture.schema.cli.tag_options import build_selector, tag_selection_options
from overture.schema.system.discovery import (
    discover_models,
    filter_models,
)

from .extraction.specs import ModelSpec
from .layout.module_layout import (
    OUTPUT_ROOT,
    compute_schema_root,
    entry_point_module,
)
from .markdown.pipeline import generate_markdown_pages
from .pyspark.pipeline import generate_pyspark_modules
from .spec_discovery import extract_model_spec

log = logging.getLogger(__name__)

__all__ = ["cli"]

_OUTPUT_FORMATS = ("markdown", "pyspark")

_FEATURE_FRONTMATTER = "---\nsidebar_position: 1\n---\n\n"


def _write_output(
    content: str,
    output_dir: Path | None,
    output_path: PurePosixPath,
) -> None:
    """Write content to a file under output_dir, or stdout."""
    if output_dir:
        file_path = output_dir / output_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    else:
        click.echo(content)
        click.echo()  # separate entries with a blank line in stdout mode


@click.group()
def cli() -> None:
    """Overture Schema code generator.

    Generate documentation and code from Pydantic schema models.
    """


@cli.command("list")
def list_models() -> None:
    """List all discovered models."""
    models = discover_models()
    names = sorted(
        model.__name__ if isinstance(model, type) else str(model)
        for model in models.values()
    )
    for name in names:
        click.echo(name)


@cli.command()
@click.option(
    "--format",
    "output_format",
    required=True,
    type=click.Choice(_OUTPUT_FORMATS),
    help="Output format",
)
@tag_selection_options
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Write output files directly into this directory (default: stdout). "
    "For pyspark, writes expression modules (*.py). "
    "For markdown, writes theme subdirectories.",
)
@click.option(
    "--test-output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Write test modules (test_*.py) into this directory (pyspark only).",
)
def generate(
    output_format: str,
    tags: tuple[str, ...],
    filters: tuple[str, ...],
    excludes: tuple[str, ...],
    output_dir: Path | None,
    test_output_dir: Path | None,
) -> None:
    """Generate code/docs from discovered models."""
    if output_format != "pyspark" and test_output_dir is not None:
        raise click.UsageError("--test-output-dir is only valid with --format pyspark")

    all_models = discover_models()

    models = filter_models(all_models, build_selector(tags, filters, excludes))

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    model_specs: list[ModelSpec] = [
        spec
        for key, entry in models.items()
        if (spec := extract_model_spec(key, entry)) is not None
    ]

    if output_format == "pyspark":
        _generate_pyspark(model_specs, output_dir, test_output_dir)
    else:
        module_paths = [entry_point_module(k.entry_point) for k in all_models]
        schema_root = compute_schema_root(module_paths)
        _generate_markdown(model_specs, schema_root, output_dir)


def _generate_markdown(
    model_specs: list[ModelSpec],
    schema_root: str,
    output_dir: Path | None,
) -> None:
    """Generate markdown with directory layout and placement-aware links."""
    pages = generate_markdown_pages(model_specs, schema_root)

    for page in pages:
        content = (
            f"{_FEATURE_FRONTMATTER}{page.content}" if page.is_model else page.content
        )
        _write_output(content, output_dir, page.path)

    if output_dir:
        feature_paths = {page.path for page in pages if page.is_model}
        all_paths = {page.path for page in pages}
        _write_category_files(output_dir, all_paths, feature_paths)


def _generate_pyspark(
    model_specs: list[ModelSpec],
    output_dir: Path | None,
    test_output_dir: Path | None = None,
) -> None:
    """Generate PySpark validation modules.

    Output is syntactically valid Python; we assume a code formatter runs
    over the written directories afterwards to match existing conventions.
    """
    modules = generate_pyspark_modules(model_specs)
    for mod in modules.source:
        _write_output(mod.content, output_dir, mod.path)
    if test_output_dir is not None:
        for mod in modules.test:
            _write_output(mod.content, test_output_dir, mod.path)


def _ancestor_dirs(paths: set[PurePosixPath]) -> set[PurePosixPath]:
    """Collect all ancestor directories for a set of file paths."""
    dirs: set[PurePosixPath] = set()
    for path in paths:
        parent = path.parent
        while parent != OUTPUT_ROOT:
            dirs.add(parent)
            parent = parent.parent
    return dirs


def _top_level_positions(
    dirs: set[PurePosixPath],
    feature_paths: set[PurePosixPath],
) -> dict[PurePosixPath, int]:
    """Assign sidebar positions: feature dirs first, then non-feature, both alphabetical."""
    feature_dir_names = {p.parts[0] for p in feature_paths}
    top_level = sorted(d for d in dirs if d.parent == OUTPUT_ROOT)
    feature_dirs = [d for d in top_level if d.name in feature_dir_names]
    non_feature_dirs = [d for d in top_level if d.name not in feature_dir_names]
    return {d: i for i, d in enumerate(feature_dirs + non_feature_dirs, start=1)}


def _write_category_files(
    output_dir: Path,
    all_paths: set[PurePosixPath],
    feature_paths: set[PurePosixPath],
) -> None:
    """Write _category_.json files for Docusaurus sidebar navigation."""
    dirs = _ancestor_dirs(all_paths)
    positions = _top_level_positions(dirs, feature_paths)

    for dir_path in sorted(dirs):
        label = dir_path.name.replace("_", " ").title()
        category: dict[str, object] = {"label": label}
        if dir_path in positions:
            category["position"] = positions[dir_path]

        file_path = output_dir / dir_path / "_category_.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(category, indent=2) + "\n")


def main() -> None:
    """Run the CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
