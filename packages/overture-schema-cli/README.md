# overture-schema-cli

The `overture-schema` command: validate Overture Maps data, generate JSON Schema, and list
the feature types you have installed.

## Installation

```bash
pip install overture-schema-cli
```

This package doesn't include any feature types. The command works on whatever theme
packages are installed alongside it. To get all six themes and the command together,
install the metapackage instead:

```bash
pip install overture-schema
```

## Usage

```bash
overture-schema list-types
overture-schema validate data.geojson
overture-schema validate - < data.geojson
overture-schema json-schema --type building > building.schema.json
```

`validate` accepts JSON, YAML, and GeoJSON: a single feature, an array of features, or a
`FeatureCollection`. It exits `0` on success and `1` on a validation failure, so it
works in CI. Pass `-` to read from stdin.

All three commands take `--tag`, `--filter`, and `--exclude` to narrow the set of feature
types. `validate` and `json-schema` also take `--type` to target one type.

For a full walkthrough, see
[Package layers](https://github.com/OvertureMaps/schema/blob/main/guides/getting-started-with-the-schema.md#package-layers) in Getting started with the schema.
