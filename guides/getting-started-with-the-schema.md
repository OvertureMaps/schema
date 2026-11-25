# Getting started with the schema

Use this tutorial to install the Overture schema packages, validate a real Overture
feature, and work with it in Python. You'll use one record throughout: the Empire State
Building, from the `2026-11-18.0` Overture release. You should know some Python, but you
don't need to know [Pydantic](https://docs.pydantic.dev/latest/).

## What you're installing

**The schema is not one Python package. It's thirteen Python packages**, all published
to [PyPI](https://pypi.org/project/overture-schema/):

```
overture-schema                  ← a metapackage: depends on the others, ships no code
overture-schema-system           ← foundations: numeric types, geometry, discovery
overture-schema-common           ← Overture conventions: OvertureFeature, names, sources
overture-schema-cli              ← the `overture-schema` command
overture-schema-validation       ← validate() / validate_json()
overture-schema-codegen          ← the `overture-codegen` command
overture-schema-pyspark          ← the `overture-validate` command
overture-schema-theme-*          ← six of these: addresses, base, buildings, divisions, places, transportation
```

Each package has its own version number. In the repo, each one lives in its own
directory under `packages/` with its own `pyproject.toml`.

They are separate packages so that **what you install decides what exists at runtime**.
Install only the buildings package (`overture-schema-theme-buildings`) and the tooling
only knows about buildings. For the reasons behind the split, see
[Many packages](concepts.md#many-packages) in our
concepts guide.

### Package layers

The packages depend on each other in one direction only. Each layer below uses the one
above it, and never the reverse. That ordering is what lets the tooling work on all feature types.

| Layer | Package | Gives you |
|---|---|---|
| Foundation | `system` | `float32`/`uint8`/…, `Geometry`, `BBox`, `CountryCodeAlpha2`, constraint annotations, `Feature` base class, entry-point discovery. None of it is Overture-specific. |
| Overture conventions | `common` | `OvertureFeature` (id/theme/type/version/geometry/sources), `@scoped`, `Names`, `Sources`, cartography hints |
| Feature types | `theme-*` | `Building`, `Place`, `Segment`, `Address`, … plus their enums |
| Tooling | `cli`, `codegen`, `pyspark`, `validation` | commands and functions that consume the above generically |

The foundation layer is the only one that isn't Overture-specific. It doesn't import from
`common` or from any theme, so you can build models with none of the Overture conventions
on `system.Feature`. Overture conventions start at `common`.

The tooling layer never hardcodes feature types. It discovers them. That's why your own
models can slot in. Most of the tooling does depend on `common`, though: `cli` and
`validation` both import `OvertureFeature`.

## Prerequisites

- **Python 3.10 or newer.** If you use `uv`, you don't need to install Python yourself.
  `uv` fetches a suitable one if your system Python is too old.
- **[`uv`](https://docs.astral.sh/uv/getting-started/installation/) or `pip`.** This guide
  writes commands for `uv`. See [Install from PyPI](#install-from-pypi) for both.

You do **not** need Java, Spark, or Homebrew for anything in this guide except the
PySpark parts. If you already have a Homebrew Spark installed, it may actively break
things. See
[`FileNotFoundError` on `spark-submit`](troubleshooting.md#filenotfounderror-on-spark-submit).

## Install from PyPI

> [!NOTE]
> To write models of your own data, follow this tutorial first, then read
> [Writing models](writing-models.md). If you'd like to propose a change to Overture's core
> schema, install from a clone instead, as in
> [Set up a clone](../CONTRIBUTING.md#set-up-a-clone).

Install the `overture-schema` metapackage with either `uv` or `pip`, not both. It pulls in
all six themes, the validation functions, and the `overture-schema` command.

If you use `uv`:

```bash
uv init my-overture-project
cd my-overture-project
uv add overture-schema
```

If you use `pip`:

```bash
mkdir my-overture-project
cd my-overture-project
python -m venv .venv
source .venv/bin/activate
pip install overture-schema
```

Commands in this guide start with `uv run`, and you run them from your project directory.
If you installed with `pip`, keep the environment active and leave off `uv run`. For more
on either tool, see uv's guide to [working on projects](https://docs.astral.sh/uv/guides/projects/)
or the Python Packaging User Guide on
[pip and virtual environments](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/).

**This is the whole install for most people.** You can now validate data, explore models,
and generate JSON Schema.

The schema has three commands, each from its own package, and the metapackage installs
only `overture-schema`.

| Command | Package | Use it to |
|---|---|---|
| `overture-schema` | [`overture-schema-cli`](../packages/overture-schema-cli/README.md) | validate files, list feature types, and generate JSON Schema |
| `overture-codegen` | [`overture-schema-codegen`](../packages/overture-schema-codegen/README.md) | generate markdown reference docs and PySpark validation code |
| `overture-validate` | [`overture-schema-pyspark`](../packages/overture-schema-pyspark/README.md) | validate Parquet data and full releases with Spark |

Add `overture-codegen` the same way you installed the metapackage: `uv add
overture-schema-codegen`, or `pip install overture-schema-codegen` if you use `pip`. Before
you add `overture-validate`, read [Install PySpark](validating-at-scale.md#install-pyspark).

### Get the sample files

Examples in these guides use sample files from the repo's `guides/examples/` folder.
Download five of them into your project, at the same paths the repo uses, so those
commands work as written:

```bash
base=https://raw.githubusercontent.com/OvertureMaps/schema/main
for f in guides/examples/buildings/empire-state-building.json \
         guides/examples/buildings/negative-height.json \
         guides/examples/places/starbucks-reserve-empire-state-building.json \
         guides/examples/divisions/manhattan.json \
         guides/examples/transportation/west-34th-street.json; do
  curl -sSf --create-dirs -o "$f" "$base/$f"
done
```

### Check the install

Run these commands. All should succeed:

```bash
uv run overture-schema --version
```

```
overture-schema, version 2.0.0
```

```bash
uv run overture-schema list-types
```

```
address            feature  overture  overture:theme=addresses
bathymetry         feature  overture  overture:theme=base
building           feature  overture  overture:theme=buildings
building_part      feature  overture  overture:theme=buildings
connector          feature  overture  overture:theme=transportation
division           feature  overture  overture:theme=divisions
division_area      feature  overture  overture:theme=divisions
division_boundary  feature  overture  overture:theme=divisions
infrastructure     feature  overture  overture:theme=base
land               feature  overture  overture:theme=base
land_cover         feature  overture  overture:theme=base
land_use           feature  overture  overture:theme=base
place              feature  overture  overture:theme=places
segment            feature  overture  overture:theme=transportation
water              feature  overture  overture:theme=base
```

```bash
uv run overture-schema validate guides/examples/buildings/empire-state-building.json
```
```
✓ Successfully validated guides/examples/buildings/empire-state-building.json
```

That file is the Empire State Building's record from the `2026-11-18.0` Overture release,
written out as GeoJSON. Here it is with the coordinates, `names`, and `sources` shortened:

```json
{
  "type": "Feature",
  "id": "0e8abfe5-a7f3-4e8e-b6f0-db1fb0bb5b0c",
  "bbox": [-73.98650360107422, 40.7479248046875, -73.98480987548828, 40.748958587646484],
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-73.9864839, 40.7485145], ...]]
  },
  "properties": {
    "theme": "buildings",
    "type": "building",
    "version": 6,
    "subtype": "commercial",
    "class": "office",
    "names": { "primary": "Empire State Building", "common": { "en": "Empire State Building", ... } },
    "height": 443.2,
    "num_floors": 102,
    "has_parts": true,
    "is_underground": false,
    "sources": [{ "dataset": "OpenStreetMap", "record_id": "w34633854@78", ... }]
  }
}
```

`theme` and `type` under `properties` tell the CLI which model to check the file against:
here, `Building`. For proof that validation is really checking something, see
[the example file](concepts.md#the-example-file).

## A complete example

Now load the same record into Python. In this example you load the feature, read it,
change it, write it back out, and confirm it still validates.

```python
import json
from overture.schema.buildings import Building

# 1. LOAD: the file is GeoJSON, so go through JSON mode
b = Building.model_validate_json(
    open("guides/examples/buildings/empire-state-building.json").read()
)
print("1. loaded :", b.id)

# 2. READ: plain Python attributes; enums come back as enum members
print("2. read   :", b.height, "m,", b.num_floors, "floors, class", b.class_.value)

# 3. MODIFY: ordinary assignment. Use the roof height instead of the antenna tip
b.height = 381.0
print("3. changed:", b.height, "m")

# 4. WRITE: by_alias=True so `class_` is written as `class`
out = b.model_dump(mode="json", by_alias=True, exclude_none=True)
print("4. wrote  :", json.dumps(out)[:70], "...")

# 5. CONFIRM: the output is valid input
again = Building.model_validate_json(json.dumps(out))
print("5. re-read:", again.height, "m")
```

```
1. loaded : 0e8abfe5-a7f3-4e8e-b6f0-db1fb0bb5b0c
2. read   : 443.2 m, 102 floors, class office
3. changed: 381.0 m
4. wrote  : {"type": "Feature", "id": "0e8abfe5-a7f3-4e8e-b6f0-db1fb0bb5b0c", "bbo ...
5. re-read: 381.0 m
```

Most code that uses the models follows the same three steps: validate the data as you
load it, work with the result as a Python object, and write it back out. In this example,
`b` is a `Building` object. You read a field with `b.height` and change it with
`b.height = 381.0`, the same way you would with any Python object.

You'll find more on three of the example's lines in
[Working with features in Python](working-with-features.md):

| Line | Why it's written that way | Where |
|---|---|---|
| `model_validate_json(...)` | the file is GeoJSON, which needs JSON mode | [Two representations](working-with-features.md#two-representations) |
| `b.class_.value` | the field is `class_` in Python, `class` in the data | [Reading fields](working-with-features.md#reading-fields) |
| `by_alias=True, exclude_none=True` | without them the output won't re-validate | [Writing data back out](working-with-features.md#writing-data-back-out) |

If the example ran, you can start using the models now. If one of those lines gives you
trouble, or you want to know why it's written that way, follow its link.

## Next steps

In this tutorial, you installed the schema packages and validated the Empire State
Building's record with the `overture-schema` command. Then you loaded the record in
Python, changed its height, and wrote it back out in a form that validates again.

Where you go next depends on what you're building:

- To look up feature types, their fields, and the values those fields accept, read
  [Exploring the models](exploring-the-models.md).
- To load, change, and write features in your own code, read
  [Working with features in Python](working-with-features.md).
- To check files or records against the schema, read [Validating data](validating-data.md).
- To build a command-line tool on the models, follow
  [Building a command-line tool on the models](building-a-command-line-tool.md).
- To define feature types of your own, read [Writing models](writing-models.md).
