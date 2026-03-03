"""CLI entry point for extracting validation rules from Overture schema models."""

from __future__ import annotations

from pathlib import Path

import click
import yaml
from pydantic import BaseModel

from overture.schema.core.discovery import ModelKey, discover_models

from .extract import extract
from .ir import DatasetSpec, ValidationSpec


def _filter_models(
    namespace: str | None,
    themes: tuple[str, ...],
    types: tuple[str, ...],
) -> dict[ModelKey, type[BaseModel]]:
    """Discover and filter models by namespace, theme, and type."""
    models = discover_models(namespace=namespace)
    if not themes and not types:
        return models

    filtered: dict[ModelKey, type[BaseModel]] = {}
    for key, model_class in models.items():
        if themes and (key.theme is None or key.theme not in themes):
            continue
        if types and key.type not in types:
            continue
        filtered[key] = model_class
    return filtered


def _extract_datasets(
    models: dict[ModelKey, type[BaseModel]],
) -> list[DatasetSpec]:
    """Extract DatasetSpec from each concrete model class."""
    datasets: list[DatasetSpec] = []
    for model_class in models.values():
        if not (isinstance(model_class, type) and issubclass(model_class, BaseModel)):
            continue
        datasets.append(extract(model_class))
    return datasets


def _dump_yaml(data: dict) -> str:
    """Serialize a dict to YAML."""
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


@click.command("overture-schema-rules")
@click.option("--namespace", default=None, help="Namespace filter (e.g. overture, annex).")
@click.option("--theme", "themes", multiple=True, help="Theme filter (repeatable).")
@click.option("--type", "types", multiple=True, help="Type filter (repeatable).")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Write one YAML file per dataset to this directory instead of stdout.",
)
@click.option("--list", "-l", "list_types", is_flag=True, help="List available types and exit.")
def cli(
    namespace: str | None,
    themes: tuple[str, ...],
    types: tuple[str, ...],
    output_dir: Path | None,
    list_types: bool,
) -> None:
    """Extract validation rules from Overture schema models."""
    models = _filter_models(namespace, themes, types)

    if list_types:
        if not models:
            click.echo("No types found.")
            return
        for key in sorted(models, key=lambda k: (k.namespace, k.theme or "", k.type)):
            parts = [key.namespace]
            if key.theme is not None:
                parts.append(key.theme)
            parts.append(key.type)
            click.echo(":".join(parts))
        return

    datasets = _extract_datasets(models)
    if not datasets:
        click.echo("No datasets matched the given filters.", err=True)
        raise SystemExit(1)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for ds in datasets:
            path = output_dir / f"{ds.name}.yaml"
            path.write_text(
                _dump_yaml(ds.model_dump(mode="json", exclude_none=True)),
                encoding="utf-8",
            )
            click.echo(f"Wrote {path}")
    else:
        spec = ValidationSpec(datasets=datasets)
        click.echo(
            _dump_yaml(spec.model_dump(mode="json", exclude_none=True)),
            nl=False,
        )
