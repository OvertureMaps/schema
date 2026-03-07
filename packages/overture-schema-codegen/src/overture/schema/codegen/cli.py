"""CLI entrypoint for schema code generation."""

import json
import logging
from pathlib import Path, PurePosixPath

import click

from overture.schema.core.discovery import discover_models

from .extraction.model_extraction import extract_model
from .extraction.specs import (
    FeatureSpec,
    is_model_class,
    is_union_alias,
)
from .extraction.union_extraction import extract_union
from .layout.module_layout import (
    OUTPUT_ROOT,
    compute_schema_root,
    entry_point_class,
    entry_point_module,
)
from .markdown.pipeline import generate_markdown_pages
from .wassirman.ir import ValidationIR
from .wassirman.pipeline import generate_validation_ir

log = logging.getLogger(__name__)

__all__ = ["cli"]

_OUTPUT_FORMATS = ("markdown", "wassirman")

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
@click.option(
    "--theme",
    multiple=True,
    help="Filter to specific theme(s); repeatable (e.g., --theme buildings --theme places)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Write output to directory (default: stdout)",
)
def generate(
    output_format: str,
    theme: tuple[str, ...],
    output_dir: Path | None,
) -> None:
    """Generate code/docs from discovered models."""
    all_models = discover_models()

    # Schema root from ALL entry points (before theme filter).
    module_paths = [entry_point_module(k.entry_point) for k in all_models]
    schema_root = compute_schema_root(module_paths)

    models = (
        {k: v for k, v in all_models.items() if k.theme in theme}
        if theme
        else all_models
    )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    feature_specs: list[FeatureSpec] = []
    for key, entry in models.items():
        if is_model_class(entry):
            feature_specs.append(extract_model(entry, entry_point=key.entry_point))
        elif is_union_alias(entry):
            feature_specs.append(
                extract_union(
                    entry_point_class(key.entry_point),
                    entry,
                    entry_point=key.entry_point,
                )
            )

    if output_format == "markdown":
        _generate_markdown(feature_specs, schema_root, output_dir)
    elif output_format == "wassirman":
        _generate_wassirman(feature_specs, output_dir)


def _generate_wassirman(
    feature_specs: list[FeatureSpec],
    output_dir: Path | None,
) -> None:
    """Generate validation IR as YAML."""
    ir = generate_validation_ir(feature_specs)
    if output_dir:
        for dataset in ir.datasets:
            file_path = output_dir / f"{dataset.name}.yaml"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            single_ir = ValidationIR(datasets=[dataset])
            file_path.write_text(single_ir.to_yaml())
    else:
        click.echo(ir.to_yaml())


def _generate_markdown(
    feature_specs: list[FeatureSpec],
    schema_root: str,
    output_dir: Path | None,
) -> None:
    """Generate markdown with directory layout and placement-aware links."""
    pages = generate_markdown_pages(feature_specs, schema_root)

    for page in pages:
        content = (
            f"{_FEATURE_FRONTMATTER}{page.content}" if page.is_feature else page.content
        )
        _write_output(content, output_dir, page.path)

    if output_dir:
        feature_paths = {page.path for page in pages if page.is_feature}
        all_paths = {page.path for page in pages}
        _write_category_files(output_dir, all_paths, feature_paths)


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
