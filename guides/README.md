# Overture schema guides

Use these guides if you want to work with the Overture schema in your own code. You can
explore the feature types and their fields, check that data follows the schema, read and
write Overture features in Python, and generate other formats, such as JSON Schema,
reference docs, Spark schemas, and types for other programming languages. You can build
your own command-line tools on the models. You can also write Pydantic models of your own
data and register them, so the Overture tools validate and document your feature types
alongside Overture's.

You should know some Python, but you don't need to know
[Pydantic](https://docs.pydantic.dev/latest/). If you're new to the schema, start with
[Getting started with the schema](getting-started-with-the-schema.md). You can also point a
coding agent at this repository and use it to explore the schema.

## Tutorials

- [Getting started with the schema](getting-started-with-the-schema.md): install the
  packages from PyPI, validate the Empire State Building's record with the
  `overture-schema` command, and load, change, and write the record in Python.
- [Building a command-line tool on the models](building-a-command-line-tool.md): build a
  command that explains where each part of a feature's data came from, and give it the
  same tag options as `overture-schema`.

## Using the schema

- [Exploring the models](exploring-the-models.md): list the installed feature types and
  select them by tag, look up each feature type's fields, constraints, and allowed values in
  Python, read the documentation for enum values, generate the JSON Schema, and generate
  markdown reference docs you can browse.
- [Working with features in Python](working-with-features.md): load GeoJSON and flat
  (Parquet-style) data into the models, read and change fields, and write features back
  out so they validate again. You'll also work with `Segment` and other discriminated
  unions, and install only the themes your application uses.
- [Validating data](validating-data.md): validate JSON, YAML, and GeoJSON files with the
  `overture-schema validate` command, including files you pipe in from a URL or from S3,
  and validate records in your own Python code.
- [Validating at scale with PySpark](validating-at-scale.md): install PySpark, validate
  Parquet data and a full Overture release in S3 with `overture-validate`, and run the same
  checks from your own PySpark code.
- [Generating other formats](generating-other-formats.md): generate PySpark validation
  code and Spark schemas (`StructType`), and generate types for other programming
  languages from the JSON Schema.
- [Explore the JSON Schema with jq](explore-json-schema-with-jq.md): find a field, look up
  its rules and valid values, and find the required fields, from the command line.
- [Generate code from the JSON Schema](generate-code-from-json-schema.md): generate types
  in Python, TypeScript, and Rust, with workarounds where a generator ignores part of the
  schema.

## Writing models

- [Writing models](writing-models.md): write Pydantic models with Overture's base classes,
  numeric types, constraints, enums, relationships, and discriminated unions. Then package
  and register them with entry points and tags so the Overture tools find them. The guide
  ends with templates you can start from.
- [Adding a codegen target](../packages/overture-schema-codegen/docs/adding-a-target.md):
  add an output format to `overture-codegen`, such as Arrow schemas or protobuf.

## Background

- [Concepts](concepts.md): why the schema uses Pydantic rather than JSON Schema, why it's
  split into many packages, how the GeoJSON envelope works, how tags work, what a
  feature's sources record, and why generated code isn't in git.
- [Glossary](glossary.md): terms for the data model and the Python toolchain.
- [Troubleshooting](troubleshooting.md): fixes for install and environment errors,
  problems pasting commands into zsh, and common mistakes with the models.

## Reference

The schema reference, with a page for every feature type, enum, and shared type, is at
[docs.overturemaps.org/schema](https://docs.overturemaps.org/schema/). It's generated from
the Pydantic models at each release. To generate the same pages for the packages you have
installed, follow
[Generate browsable reference docs](exploring-the-models.md#generate-browsable-reference-docs).

For every option of a command or function, see that package's `README.md` under
[`packages/`](../packages/).

## Contributing

To change this repository, read [CONTRIBUTING.md](../CONTRIBUTING.md).
