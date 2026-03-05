"""CLI entry point for Overture schema validation tools."""

from __future__ import annotations

from pathlib import Path

import click
import yaml
from pydantic import BaseModel

from overture.schema.core.discovery import ModelKey, discover_models

from .extract import extract
from .ir import CheckType, DatasetSpec, ValidationSpec


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


@click.group("overture-schema-validation")
def cli() -> None:
    """Overture schema validation tools."""


@cli.command("extract")
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
def extract_cmd(
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


@cli.command("validate")
@click.option("--type", "type_name", required=True, help="Feature type to validate.")
@click.option("--theme", default=None, help="Theme filter.")
@click.option(
    "--input",
    "-i",
    "input_path",
    required=True,
    help="Input parquet path (supports glob).",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Output parquet path for violations.",
)
@click.option(
    "--engine",
    type=click.Choice(["duckdb", "pyspark"]),
    default="duckdb",
    help="Validation engine.",
)
def validate_cmd(
    type_name: str,
    theme: str | None,
    input_path: str,
    output_path: Path,
    engine: str,
) -> None:
    """Validate parquet data against schema rules."""
    themes = (theme,) if theme else ()
    models = _filter_models(namespace=None, themes=themes, types=(type_name,))

    if len(models) == 0:
        click.echo(f"No model matched type '{type_name}'.", err=True)
        raise SystemExit(1)
    if len(models) > 1:
        matched = ", ".join(
            f"{k.namespace}:{k.theme}:{k.type}" for k in models
        )
        click.echo(
            f"Multiple models matched type '{type_name}': {matched}. "
            "Use --theme to disambiguate.",
            err=True,
        )
        raise SystemExit(1)

    model_class = next(iter(models.values()))
    spec = extract(model_class)

    if engine == "pyspark":
        _validate_pyspark(spec, input_path, output_path)
    else:
        _validate_duckdb(spec, input_path, output_path)


def _validate_duckdb(spec, input_path: str, output_path: Path) -> None:
    """Run validation using the DuckDB engine."""
    try:
        from .duckdb import compile, connect
    except ImportError:
        click.echo(
            "duckdb is required for the validate command with --engine duckdb. "
            "Install it with: pip install overture-schema-validation[duckdb]",
            err=True,
        )
        raise SystemExit(1)

    sql = compile(spec, input_path)

    conn = connect()
    if any(r.check == CheckType.GEOMETRY_TYPE for r in spec.rules):
        conn.execute("INSTALL spatial; LOAD spatial;")

    conn.execute(
        f"COPY ({sql}) TO '{output_path}' (FORMAT PARQUET)",
        [input_path],
    )

    count = conn.execute(
        f"SELECT count(*) FROM '{output_path}'"
    ).fetchone()[0]

    click.echo(f"{count} violation(s) written to {output_path}", err=True)


def _validate_pyspark(spec, input_path: str, output_path: Path) -> None:
    """Run validation using the PySpark engine."""
    try:
        from .pyspark import create_spark_session, validate_df
    except ImportError:
        click.echo(
            "pyspark is required for the validate command with --engine pyspark. "
            "Install it with: pip install overture-schema-validation[pyspark]",
            err=True,
        )
        raise SystemExit(1)

    try:
        spark = create_spark_session()
    except Exception as exc:
        if "getSubject is not supported" in str(exc):
            click.echo(
                "PySpark 3.5 requires Java 17 or 21. Your current Java version "
                "is not compatible. Set JAVA_HOME to a supported JDK, e.g.:\n"
                "  export JAVA_HOME=$(/usr/libexec/java_home -v 17)",
                err=True,
            )
            raise SystemExit(1)
        raise
    df = spark.read.parquet(input_path)
    violations = validate_df(spec, df, spark)
    violations.write.mode("overwrite").parquet(str(output_path))
    count = violations.count()
    click.echo(f"{count} violation(s) written to {output_path}", err=True)
    spark.stop()
