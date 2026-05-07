"""CLI entry point for validation."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass

import click
from pyspark.sql import DataFrame, SparkSession

from overture.schema.system.discovery import resolve_entry_point_key
from overture.schema.system.primitive import GeometryType

from ._registry import PARTITION_MAP, REGISTRY
from .validate import (
    explain_errors,
    feature_names,
    validate_feature,
)


@dataclass(frozen=True)
class ReadSpec:
    """Parquet read plan.

    `data_path` selects the files to read; `base_path`, when set, tells
    Spark where to start discovering Hive partition columns.
    """

    data_path: str
    base_path: str | None = None


def resolve_read(path: str, partitions: Mapping[str, str] | None) -> ReadSpec:
    """Determine read strategy from path structure.

    Three cases:

    1. **Hive partition path** (contains `/{key}=` for some key in
       `partitions`) -- derive `basePath` so Spark discovers partition
       columns.
    2. **Individual file** (`*.parquet`) or no partitions -- read
       directly; data already contains the partition columns inline.
    3. **Release root** -- append the partition path
       (`key1=v1/key2=v2/...`) and set `basePath` to the original path.
    """
    stripped = path.rstrip("/")

    # Path already contains Hive partition directories
    for key in partitions or ():
        idx = stripped.find(f"/{key}=")
        if idx >= 0:
            return ReadSpec(data_path=path, base_path=stripped[:idx])

    # Individual file or no partition mapping — data has partition columns inline
    if stripped.endswith(".parquet") or not partitions:
        return ReadSpec(data_path=path)

    # Release root — construct leaf path from partition map
    partition_path = "/".join(f"{k}={v}" for k, v in partitions.items())
    return ReadSpec(
        data_path=f"{stripped}/{partition_path}",
        base_path=stripped,
    )


def read_feature(spark: SparkSession, spec: ReadSpec) -> DataFrame:
    """Read a DataFrame according to a ReadSpec."""
    reader = spark.read
    if spec.base_path:
        reader = reader.option("basePath", spec.base_path)
    return reader.parquet(spec.data_path)


_S3A_DEFAULTS: dict[str, str] = {
    "spark.jars.packages": "org.apache.hadoop:hadoop-aws:3.4.1",
    "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
    "spark.hadoop.fs.s3a.aws.credentials.provider": (
        "org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider"
    ),
}

_LARGE_GEOMETRY_TYPES = frozenset(
    {
        GeometryType.LINE_STRING,
        GeometryType.MULTI_LINE_STRING,
        GeometryType.POLYGON,
        GeometryType.MULTI_POLYGON,
        GeometryType.GEOMETRY_COLLECTION,
    }
)


def _may_have_large_geometry(feature_key: str) -> bool:
    """Whether a registered feature's geometries may be large.

    Returns True when the registered geometry types include
    (multi)linestrings, (multi)polygons, or geometry collections,
    or when geometry types are unspecified (safe default).
    """
    validation = REGISTRY[feature_key]
    if not validation.geometry_types:
        return True
    return bool(set(validation.geometry_types) & _LARGE_GEOMETRY_TYPES)


def _spark_config(path: str, conf: tuple[str, ...], feature_key: str) -> dict[str, str]:
    """Build Spark config dict with safe defaults.

    Disables the vectorized Parquet reader for features with large
    geometries (polygons, linestrings) to avoid OOM on WKB binary
    columns.  Adds S3A credentials for `s3a://` paths.  User-supplied
    `--conf` values override any defaults.
    """
    config: dict[str, str] = {}
    if _may_have_large_geometry(feature_key):
        config["spark.sql.parquet.enableVectorizedReader"] = "false"
    if path.startswith("s3a://"):
        config.update(_S3A_DEFAULTS)
    for pair in conf:
        key, _, value = pair.partition("=")
        config[key] = value
    return config


@click.command("overture-validate")
@click.argument("feature_type")
@click.argument("path")
@click.option("-o", "--output", default=None, help="Output path for validated Parquet.")
@click.option(
    "--head",
    "head_n",
    default=20,
    type=int,
    show_default=True,
    help="Error rows to display.",
)
@click.option("--conf", multiple=True, help="Spark config key=value pairs.")
@click.option(
    "--count-only",
    is_flag=True,
    default=False,
    help="Report error count only; skip explain/unpivot.",
)
@click.option(
    "--skip-schema-check",
    is_flag=True,
    default=False,
    help="Warn on schema mismatches instead of aborting.",
)
@click.option(
    "--skip-columns",
    multiple=True,
    help="Columns declared absent from data; skips their checks.",
)
@click.option(
    "--ignore-extra-columns",
    multiple=True,
    help="Extra data columns to ignore in schema comparison.",
)
@click.option(
    "--suppress",
    "suppress_specs",
    multiple=True,
    help="Suppress checks: FIELD (all checks) or FIELD:CHECK (specific).",
)
def validate_cli(
    feature_type: str,
    path: str,
    output: str | None,
    head_n: int,
    conf: tuple[str, ...],
    count_only: bool,
    skip_schema_check: bool,
    skip_columns: tuple[str, ...],
    ignore_extra_columns: tuple[str, ...],
    suppress_specs: tuple[str, ...],
) -> None:
    """Validate Overture data at PATH and write annotated Parquet."""
    try:
        resolved = resolve_entry_point_key(feature_type, REGISTRY)
    except ValueError:
        click.echo(
            f"Unknown type '{feature_type}'. Known: {', '.join(feature_names())}",
            err=True,
        )
        sys.exit(1)

    builder = SparkSession.builder
    for key, value in _spark_config(path, conf, resolved).items():
        builder = builder.config(key, value)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    spec = resolve_read(path, PARTITION_MAP.get(resolved))
    df = read_feature(spark, spec)

    suppress: list[str | tuple[str, str]] = []
    for s in suppress_specs:
        if ":" in s:
            field, name = s.split(":", 1)
            suppress.append((field, name))
        else:
            suppress.append(s)

    try:
        result = validate_feature(
            df,
            resolved,
            skip_columns=skip_columns,
            ignore_extra_columns=ignore_extra_columns,
            suppress=suppress,
        )
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    if result.schema_mismatches:
        click.echo(f"Schema mismatches for {resolved}:", err=True)
        for m in result.schema_mismatches:
            click.echo(f"  {m.path}: expected {m.expected}, got {m.actual}", err=True)
        if not skip_schema_check:
            sys.exit(1)

    total_rows, error_count = result.row_counts()
    click.echo(f"{error_count} / {total_rows} rows with errors", err=True)

    if error_count > 0:
        if not count_only:
            explained = explain_errors(result.evaluated, result.checks).drop("geometry")
            if output and head_n > 0:
                explained = explained.cache()
            if output:
                explained.write.mode("overwrite").parquet(output)
                click.echo(f"Written to {output}", err=True)
            if head_n > 0:
                explained.show(head_n, truncate=False)
        sys.exit(1)
