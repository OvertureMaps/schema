# Generating other formats

Use this guide to turn the schema into other formats: PySpark validation code, Spark
schemas, and types for other programming languages. JSON Schema and markdown reference
docs are in [Exploring the models](exploring-the-models.md), because you also use them to
explore the models.

| Target | Command | Output | Where |
|---|---|---|---|
| JSON Schema | `overture-schema json-schema` | A JSON Schema document on stdout | [The generated JSON Schema](exploring-the-models.md#the-generated-json-schema) |
| Markdown | `overture-codegen generate --format markdown` | Docusaurus-ready reference pages | [Generate browsable reference docs](exploring-the-models.md#generate-browsable-reference-docs) |
| PySpark | `overture-codegen generate --format pyspark` | Python modules of `Check` builders and a `StructType` | [PySpark expressions and Spark schemas](#pyspark-expressions-and-spark-schemas) |
| Spark `StructType` | Python, through the PySpark registry | A Spark schema object | [PySpark expressions and Spark schemas](#pyspark-expressions-and-spark-schemas) |
| Another language | A JSON Schema code generator | Types in that language | [Client code in other languages](#client-code-in-other-languages) |

## PySpark expressions and Spark schemas

A [Spark schema](glossary.md#spark-schema), or `StructType`, describes the columns in a
Spark DataFrame: each column's name, its type, and whether it can be null. The PySpark
package provides one for each feature type, along with the validation checks.
Install PySpark first, as in
[Install PySpark](validating-at-scale.md#install-pyspark).

To generate the PySpark validation code yourself:

```bash
uv run overture-codegen generate --format pyspark --output-dir ./ps --test-output-dir ./ps-tests
```

You get one module per feature type, mirroring the Python package layout:

```
ps/overture/schema/buildings/building.py
ps/overture/schema/buildings/building_part.py
ps-tests/overture/schema/buildings/test_building.py
```

Each module is auto-generated (`# Do not edit`) and contains one builder function per
constraint, returning a `Check` with an unevaluated PySpark `Column`:

```python
def _version_bounds_check() -> Check:
    return Check(
        field="version",
        name="bounds",
        expr=check_bounds(F.col("version"), ge=0),
        shape=CheckShape.SCALAR,
        root_field="version",
    )
```

Plus a `MODEL_VALIDATION` constant pairing the checks with the expected `StructType`.

**To get a Spark schema for a feature type**, which is useful for `spark.read.schema(...)`,
Delta table creation, or comparing against your own tables:

```python
from overture.schema.pyspark._registry import REGISTRY
from overture.schema.pyspark.validate import resolve_entry_point_key

key = resolve_entry_point_key("building", REGISTRY)
struct = REGISTRY[key].schema

type(struct).__name__  # 'StructType'
[(f.name, f.dataType.simpleString()) for f in struct.fields][:5]
```

```
[('id', 'string'),
 ('bbox', 'struct<xmin:double,xmax:double,ymin:double,ymax:double>'),
 ('geometry', 'binary'),
 ('theme', 'string'),
 ('type', 'string')]
```

`REGISTRY` is keyed by the full entry-point string
(`"overture.schema.buildings:Building"`), which is why the `resolve_entry_point_key`
step is there. It accepts the short alias too. `ModelValidation` exposes `.schema`,
`.checks`, and `.geometry_types`.

Since `StructType` has `.json()` and `.jsonValue()`, this is also your route to an
Arrow/Parquet schema.

For the generator's own architecture and programmatic API, including the shape extraction
layer these modules are rendered from, see
[`packages/overture-schema-codegen/README.md`](../packages/overture-schema-codegen/README.md).
To write a new output format, see [Adding a codegen target](../packages/overture-schema-codegen/docs/adding-a-target.md).

## Client code in other languages

To use the schema from a language other than Python, generate its JSON Schema and give it
to a code generator for that language: for example, datamodel-code-generator for Python,
quicktype for TypeScript and many other languages, or typify for Rust. The generated types
check structure and types, but not every rule in the schema. quicktype and typify also
ignore the `patternProperties` keyword that the schema uses for `names.common`, so you
need a workaround for each.

For worked examples in Python, TypeScript and Rust, including the workarounds, see
[Generate code from the JSON Schema](generate-code-from-json-schema.md).

## Next steps

- [Generate code from the JSON Schema](generate-code-from-json-schema.md)
- [Adding a codegen target](../packages/overture-schema-codegen/docs/adding-a-target.md)
- [`overture-schema-codegen` README](../packages/overture-schema-codegen/README.md)
