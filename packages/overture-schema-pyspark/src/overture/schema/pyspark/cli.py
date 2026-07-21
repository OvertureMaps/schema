"""CLI entry point for validation."""

from __future__ import annotations

import sys
from collections.abc import Collection, Mapping
from dataclasses import dataclass

import click
from pyspark.errors import AnalysisException
from pyspark.sql import DataFrame, SparkSession

from overture.schema.system.discovery import resolve_entry_point_key
from overture.schema.system.primitive import GeometryType

from ._registry import PARTITION_MAP, REGISTRY
from .validate import (
    explain_errors,
    model_names,
    validate_model,
)


@dataclass(frozen=True)
class ReadSpec:
    """Parquet read plan.

    `data_path` selects the files to read; `base_path`, when set, tells
    Spark where to start discovering Hive partition columns.
    """

    data_path: str
    base_path: str | None = None


def absent_column(exc: AnalysisException, columns: Collection[str]) -> str | None:
    """Return the top-level column named by an unresolved-column error, if absent.

    Returns the column name only when `exc` is an `UNRESOLVED_COLUMN` error
    whose target is genuinely missing from `columns` -- the case a re-run with
    `--skip-columns` resolves.  Every other `AnalysisException` (a struct field
    accessed on a scalar, a type mismatch, an unresolved column that is in fact
    present) returns None, marking it a generator or expression bug to surface
    rather than steer toward `--skip-columns`.

    Parameters
    ----------
    exc
        The exception raised while Spark planned the check expressions.
    columns
        The data's top-level column names (`df.columns`).
    """
    # getCondition() is pyspark 4.0+; the 3.4 floor exposes the same value as
    # getErrorClass() (renamed, then deprecated, in 4.0).
    get_condition = getattr(exc, "getCondition", None)
    condition = get_condition() if get_condition is not None else exc.getErrorClass()
    if condition is None or not condition.startswith("UNRESOLVED_COLUMN"):
        return None
    object_name = (exc.getMessageParameters() or {}).get("objectName")
    if not object_name:
        return None
    # objectName is backtick-quoted, e.g. `phantom` or `bbox`.`xmin`; the
    # top-level segment is the column df.columns would carry.
    top_level = object_name.split(".", 1)[0].strip("`")
    return top_level if top_level not in columns else None


def resolve_read(path: str, partitions: Mapping[str, str] | None) -> ReadSpec:
    """Determine read strategy from path structure.

    The partition map is an ordered Hive hierarchy
    (`{"theme": "buildings", "type": "building"}`). A path supplies a
    prefix of it; the leaves below the deepest level already present are
    appended so the read always lands on a single feature type. Cases:

    1. **Individual file** (`*.parquet`) or no partitions -- read
       directly; data already contains the partition columns inline.
    2. **Release root** (no partition directories) -- append the full
       partition path and set `basePath` to the original path.
    3. **Partial partition path** (`theme=X/`) -- append the missing
       leaves (`type=Y`) so a single feature's checks aren't run against
       every type sharing the theme directory.
    4. **Leaf partition path** (`theme=X/type=Y/`) -- nothing to append;
       read it directly with `basePath` derived.
    """
    stripped = path.rstrip("/")

    # Individual file or no partition mapping — data has partition columns inline
    if stripped.endswith(".parquet") or not partitions:
        return ReadSpec(data_path=path)

    keys = list(partitions)
    # Partition levels already present in the path, in hierarchy order.
    present = [i for i, key in enumerate(keys) if f"/{key}=" in stripped]
    depth = present[-1] + 1 if present else 0  # count of levels already filled
    leaves = "/".join(f"{key}={partitions[key]}" for key in keys[depth:])

    if not present:
        # Release root — append the full partition path; it is the base.
        return ReadSpec(data_path=f"{stripped}/{leaves}", base_path=stripped)

    # Path already contains partition directories: the base is the release
    # root (before the first one); append any leaves below the deepest
    # present level (none for a leaf path, which then reads as-is).
    base_idx = stripped.find(f"/{keys[present[0]]}=")
    data_path = f"{stripped}/{leaves}" if leaves else path
    return ReadSpec(data_path=data_path, base_path=stripped[:base_idx])


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
            f"Unknown type '{feature_type}'. Known: {', '.join(model_names())}",
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
        result = validate_model(
            df,
            resolved,
            skip_columns=skip_columns,
            ignore_extra_columns=ignore_extra_columns,
            suppress=suppress,
        )
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except AnalysisException as e:
        # Backstop, narrowed to the one cause `--skip-columns` can address: a
        # check that names a column missing from the data.  validate_model
        # already drops checks for skipped and schema-absent columns, so this
        # fires only on a column outside the expected schema -- offer the
        # operator the skip lever and name the column.  Every other
        # AnalysisException (a type mismatch, a struct field read off a scalar)
        # is a generator bug `--skip-columns` cannot fix; let it propagate as a
        # traceback rather than mask it behind the skip hint.
        column = absent_column(e, df.columns)
        if column is None:
            raise
        click.echo(
            f"A check references column '{column}', absent from the data at {path}.",
            err=True,
        )
        click.echo(
            f"Re-run with `--skip-columns {column}` to skip its checks, "
            "or `--skip-schema-check`.",
            err=True,
        )
        sys.exit(1)

    if result.schema_mismatches:
        click.echo(f"Schema mismatches for {resolved}:", err=True)
        for m in result.schema_mismatches:
            click.echo(f"  {m.path}: expected {m.expected}, got {m.actual}", err=True)
        if result.absent_columns:
            flags = " ".join(f"--skip-columns {c}" for c in result.absent_columns)
            click.echo(
                f"  Re-run with `{flags}` to skip missing columns.",
                err=True,
            )
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
