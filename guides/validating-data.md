# Validating data

Use this guide to check that data follows the schema. For one file or a few, use the
`overture-schema validate` command. To validate in your own Python code, use the
validation functions. For large Parquet datasets or a full release, read
[Validating at scale with PySpark](validating-at-scale.md) instead. To test changes to the
schema itself, see [Tests and checks](../CONTRIBUTING.md#tests-and-checks).

## Files with the CLI

You can validate JSON, YAML, and GeoJSON files. Each file can hold a single feature, a JSON
array of features, or a `FeatureCollection`:

```bash
uv run overture-schema validate guides/examples/buildings/empire-state-building.json
```

```
✓ Successfully validated guides/examples/buildings/empire-state-building.json
```

Failures come back as a rendered table showing the offending value in context:

```bash
uv run overture-schema validate --show-field id guides/examples/buildings/negative-height.json
```

```
  ⚠ Ambiguous: Data matches multiple types equally. Consider:
    • Specifying --tag or --type to narrow validation
    • Adding discriminator fields to clarify intent

 ─ Validation Failed id=0e8abfe5-a7f3-4e8e-b6f0-db1fb0... ──────────────────────
          ...
           id "0e8abfe5-a7f3-4e8e-b6f0-db1fb…
        names          primary: "Empire State
                                    Building"
       height                              -5 ← Input should be greater than 0
   num_floors                             102
          ...
 ──────────────────────────────────────────────────────────────────────────────
```

For a collection, errors are indexed and labeled by the model that best fit:

```
 ─ [1] (Building) ─────────────────────────────────────────────────────────────
          ...
        names          primary: "Empire State
                                    Building"
       height                              -5 ← Input should be greater than 0
   num_floors                             102
          ...
 ──────────────────────────────────────────────────────────────────────────────
```

Without options, the CLI checks the file against every installed feature type. When the
data fails, it can't always tell which type you meant, so it prints the "Ambiguous"
warning above the table. To remove the warning, tell it the type with `--type` or narrow
the set with `--tag`:

```bash
uv run overture-schema validate --type building guides/examples/buildings/negative-height.json
```

`validate` also takes the tag options from [Listing feature types](exploring-the-models.md#listing-feature-types).
`--show-field id` changes the output only when validation fails: it adds the feature's
`id` to the heading of each failure, so you can tell which feature failed.

The command exits with `0` on success and `1` on a validation failure, so you can use it in
CI as is. For every option, see the
[`overture-schema-cli` README](../packages/overture-schema-cli/README.md).

Every check comes from the model definition. Nothing is hand-written per file. Copy an
example, edit a field, and you can watch each kind fire:

| Edit | What validation says |
|---|---|
| `"class": "office"` → `"class": "skyscraper"` | `Input should be 'agricultural', 'allotment_house', ...` |
| `"num_floors": 102` → `"num_floors": 102.5` | `Input should be a valid integer, got a number with a fractional part` |
| delete the `"theme"` property | `Ambiguous: Data matches multiple types equally` |

What it does **not** catch: free-form string fields accept any string, and nothing checks
fields against each other unless the model declares a rule for it. No rule ties `height`
to `min_height`, for example, so a building with a floor above its roof validates:

```python
import json
from overture.schema.buildings import Building

d = json.load(open("guides/examples/buildings/empire-state-building.json"))
d["properties"]["height"] = 5
d["properties"]["min_height"] = 100  # a floor above the roof
print("accepted:", Building.model_validate_json(json.dumps(d)).height)
```

```
accepted: 5.0
```

Passing validation means the data follows the schema's rules. It doesn't mean the data is
accurate.

### Data that isn't in a local file

To validate data from a URL, from S3, or from another program, pipe it to
`overture-schema validate` and pass `-` as the file name. `-` tells the command to read
from stdin:

```bash
curl -sSf https://raw.githubusercontent.com/OvertureMaps/schema/main/guides/examples/buildings/empire-state-building.json \
  | uv run overture-schema validate -
```

```
✓ Successfully validated <stdin>
```

Any command that writes the data to stdout works the same way, such as
`aws s3 cp s3://... -` or a database export. The output names the input `<stdin>`
instead of a file name.

`overture-schema validate` doesn't fetch URLs itself. If you pass it one, it reports that
the URL is not a file.

To validate large datasets in S3 without downloading them, see
[Validating at scale with PySpark](validating-at-scale.md).

## In Python code

To validate data from your own Python code, call `validate_json()` for GeoJSON or
`validate()` for flat data. You'd do this as a step in a data pipeline, for example. Both functions
check the record against every installed feature type and return a model object of the
type that matched:

```python
from overture.schema.validation import validate_json

feature = validate_json(
    open("guides/examples/buildings/empire-state-building.json").read()
)
type(feature).__name__  # 'Building'
```

Both raise `pydantic.ValidationError` when nothing matches. The mode rule from
[Two representations](working-with-features.md#two-representations) applies here too: `validate()` wants flat
data, and `validate_json()` wants GeoJSON. Install more theme packages and these functions
accept more types.

This loop validates every file in `guides/examples/`:

```python
from pathlib import Path
from pydantic import ValidationError
from overture.schema.validation import validate_json

ok, bad = 0, []
for path in sorted(Path("guides/examples").glob("*/*.json")):
    try:
        validate_json(path.read_text())
        ok += 1
    except ValidationError as e:
        bad.append((path.name, e.errors()))

print(f"{ok} valid, {len(bad)} invalid")
```
```
2 valid, 1 invalid
```

For newline-delimited GeoJSON, loop over the lines of the file instead and pass each line
to `validate_json()`.

`e.errors()` gives you structured dicts with `loc`, `msg`, `type`, and `input`, the
right thing to log or turn into a report. Package reference:
[`packages/overture-schema-validation/README.md`](../packages/overture-schema-validation/README.md).

If you know the type, validate against it directly for better errors and speed:

```python
from overture.schema.buildings import Building

Building.model_validate_json(
    open("guides/examples/buildings/empire-state-building.json").read()
)
```

## Next steps

- [Validating at scale with PySpark](validating-at-scale.md)
- [Troubleshooting](troubleshooting.md), for error messages
- [`overture-schema-cli` README](../packages/overture-schema-cli/README.md), for every option
  of `overture-schema validate`
