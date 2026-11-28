# Validating at scale with PySpark

Use this guide to validate large Parquet datasets, including a full Overture release, with
Spark. Most people don't need it. To validate a few files, or records in your own Python
code, read [Validating data](validating-data.md).

## Install PySpark

Check whether you need PySpark for what you want to do:

| I want to… | Need PySpark? |
|---|---|
| Validate files, explore models, write Python against them | **No** |
| Generate JSON Schema or markdown docs | **No** |
| Generate an SDK in another language | **No** |
| Validate millions of rows of Parquet, or data in S3 | **Yes** |
| Get a Spark `StructType` for a feature type | **Yes** |

If you don't need PySpark, read [Validating data](validating-data.md) instead.

**If yes:** add the PySpark package with its `spark` extra.
The extra pulls in PySpark itself; without it you get the `overture-validate` command but
no Spark to run it on. Quote the argument so your shell leaves the brackets alone:

```bash
uv add "overture-schema-pyspark[spark]"
```

If you use `pip`:

```bash
pip install "overture-schema-pyspark[spark]"
```

That's all. The published package already contains the generated validation
expressions. PySpark needs a Java runtime, so install one if you don't have it.

Working from a clone of the repo? See
[Generate the PySpark expressions](../CONTRIBUTING.md#generate-the-pyspark-expressions) in CONTRIBUTING.md.

## Validate with `overture-validate`

`overture-validate` validates Parquet data with Spark. When you run it, it starts a Spark session on your
machine, reads the data with Spark, and checks every row. Install it first, as in
[Install PySpark](#install-pyspark). From a clone, generate the expressions
first; see [Generate the PySpark expressions](../CONTRIBUTING.md#generate-the-pyspark-expressions).

It takes a feature type and a path to Parquet data. The examples here read from the latest
Overture release. Read its version, such as `2026-11-18.0`, from Overture's STAC catalog.
This needs [`jq`](https://jqlang.org/):

```bash
RELEASE=$(curl -s https://stac.overturemaps.org/catalog.json | jq -r .latest)
```

> [!WARNING]
> **Don't hardcode a release version.** The public bucket keeps only the last two releases,
> so a version written into a script stops working within a couple of months.

To try it, save a small sample from the release with [DuckDB](https://duckdb.org/). This saves the segments in a few blocks of
Midtown Manhattan, around the Empire State Building:

```bash
duckdb -c "
  INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;
  SET s3_region = 'us-west-2';
  COPY (
    SELECT *
    FROM read_parquet('s3://overturemaps-us-west-2/release/$RELEASE/theme=transportation/type=segment/*', hive_partitioning = 1)
    WHERE bbox.xmin > -73.995 AND bbox.xmax < -73.975
      AND bbox.ymin > 40.744 AND bbox.ymax < 40.754
  ) TO 'midtown-segments.parquet' (FORMAT PARQUET)"

uv run overture-validate segment midtown-segments.parquet
```

`hive_partitioning = 1` keeps the `theme` and `type` columns in the file, which
`overture-validate` needs when you give it a single file.

After Spark's startup messages, the last line reports how many rows had errors:

```
0 / 1529 rows with errors
```

The number of rows depends on the release.

> [!TIP]
> To hide most of Spark's log messages, save a logging configuration in a folder of its
> own and point Spark at that folder with `SPARK_CONF_DIR`. Setting `SPARK_LOCAL_IP`
> removes the warning about your hostname:
>
> ```bash
> mkdir -p ~/.spark-conf
> cat > ~/.spark-conf/log4j2.properties <<'EOF'
> rootLogger.level = error
> rootLogger.appenderRef.console.ref = console
> appender.console.type = Console
> appender.console.name = console
> appender.console.target = SYSTEM_ERR
> appender.console.layout.type = PatternLayout
> appender.console.layout.pattern = %m%n
> EOF
> export SPARK_CONF_DIR=~/.spark-conf
> export SPARK_LOCAL_IP=127.0.0.1
> ```
>
> A few lines still print before Spark reads the configuration. To also hide the progress
> bar, add `--conf spark.ui.showConsoleProgress=false` to the command.

Other common forms:

```bash
uv run overture-validate segment midtown-segments.parquet --count-only
uv run overture-validate segment midtown-segments.parquet --suppress version:bounds -o violations.parquet
uv run overture-validate segment "s3a://overturemaps-us-west-2/release/$RELEASE"
```

> [!CAUTION]
> **The last command validates every segment in the release, worldwide.** That's hundreds
> of millions of rows, and on a laptop it takes hours.

`overture-validate` handles S3A and anonymous credentials for the public Overture bucket automatically,
and expands a release root into the Hive partition path for you. The flags shown above
are the common ones. For the full list, including output paths, error-row limits, Spark
config, and schema-mismatch and check suppression, see
[`packages/overture-schema-pyspark/README.md`](../packages/overture-schema-pyspark/README.md).

### Validating with PySpark in Python

To run the same checks from your own Spark code:

```python
from pyspark.sql import SparkSession
from overture.schema.pyspark import validate_model, explain_errors

spark = SparkSession.builder.getOrCreate()
df = spark.read.parquet("s3a://.../theme=buildings/type=building/")

result = validate_model(df, "building")
result.evaluated.cache()

total = result.evaluated.count()
errors = result.error_rows().count()
print(f"{errors} / {total} rows with errors")

if errors:
    violations = explain_errors(result.evaluated, result.checks)
    violations.select("id", "field", "check", "message").show(truncate=False)
```

`validate_model` accepts either the short name (`"building"`) or the full entry-point key
(`"overture.schema.buildings:Building"`). It looks up the feature type in the registry,
compares the DataFrame schema against the expected one, and evaluates every check in a
single pass, with no per-row Python, so it scales.

| Function | Returns | Purpose |
|---|---|---|
| `validate_model(df, type)` | `ValidationResult` | Registry lookup, schema comparison, check evaluation |
| `result.error_rows()` | `DataFrame` | Rows with at least one violation |
| `explain_errors(evaluated, checks)` | `DataFrame` | One row per violation: `field`, `check`, `message` |
| `model_names()` | `list[str]` | Available type names |

Tuning, partition handling, and the rest of the PySpark API are documented in
[`packages/overture-schema-pyspark/README.md`](../packages/overture-schema-pyspark/README.md).
If `model_names()` comes back empty, see
[Troubleshooting](troubleshooting.md#model_names-returns--or-keyerror-on-a-feature-type).

## Next steps

- [Generating other formats](generating-other-formats.md#pyspark-expressions-and-spark-schemas),
  for Spark schemas and the generated PySpark code
- [`overture-schema-pyspark` README](../packages/overture-schema-pyspark/README.md)
- [Troubleshooting](troubleshooting.md)
