# Working with features in Python

Use this guide to put the models to work: load data into them, read and change it, and
write it back out. You'll also learn how to depend on only the themes you use, and how to
build a command-line tool on the models. To find out which feature types and fields you
have, read [Exploring the models](exploring-the-models.md) first.

## Two representations

Overture releases its data as Parquet files, where each field is a column. The models can
also read and write GeoJSON, for tools that work with features instead of table rows. The
generated [JSON Schema](exploring-the-models.md#the-generated-json-schema) describes the GeoJSON form. **Which form you get
depends on the Pydantic method you call, not on the data you pass.**

| Shape | Looks like | Pydantic mode | Validate with | Dump with |
|---|---|---|---|---|
| **GeoJSON** | `id`/`geometry` at top level, everything else under `properties` | `json` | `model_validate_json()` | `model_dump(mode="json")`, `model_dump_json()` |
| **Flat / tabular** (Parquet-style) | every field at the top level | `python` | `model_validate()` | `model_dump(mode="python")` |

This is a common mistake. Passing a GeoJSON *dict* to `model_validate()` fails,
because `model_validate` is Python mode and Python mode expects the flat shape:

```python
import json
from overture.schema.buildings import Building

doc = json.load(
    open("guides/examples/buildings/empire-state-building.json")
)  # a GeoJSON-shaped dict

Building.model_validate(doc)
# ValidationError: 3 validation errors for building
#   theme     Field required
#   type      Input should be 'building'   [got 'Feature']
#   version   Field required
```

The `type: Feature` in the error message shows what happened: it read the GeoJSON envelope's
`type` as the feature's `type` field.

To fix it, round-trip through JSON so you're in JSON mode:

```python
building = Building.model_validate_json(json.dumps(doc))  # works
```

Or, if you're already reading from a file or an HTTP response, skip the parse entirely:

```python
building = Building.model_validate_json(
    open("guides/examples/buildings/empire-state-building.json").read()
)
```

### No JSON mode for `model_validate`

You can't switch `model_validate` into JSON mode by passing an argument. Neither of these
works:

```python
Building.model_validate(doc, context={"mode": "json"})  # still ValidationError
Building.model_validate(doc, strict=False)  # still ValidationError
```

The mode isn't a setting you pass. In Pydantic it's determined by *which method you
call*. `model_validate` is Python mode; `model_validate_json` is JSON mode. The base
`Feature` class checks which mode is in use:

```python
@model_validator(mode="wrap")
def __validate_with_geo_json_support__(cls, data, handler, info):
    if info.mode == "json":  # <- set by the method, not by an argument
        ...  #    unpack the GeoJSON envelope
```

So if you have a GeoJSON **dict** in hand, `json.dumps` it and use
`model_validate_json`. The round-trip is slightly wasteful but it is the supported path:

```python
Building.model_validate_json(json.dumps(doc))
```

Better still, avoid making the dict at all. If the GeoJSON came from a file or an HTTP
response, hand the raw text straight to `model_validate_json` and skip `json.loads`
entirely. The one case where you can't is YAML. There's no YAML mode, so load it with
`yaml.safe_load`, then pass `json.dumps` of the result to `model_validate_json`.

### Reading the error

A mode mismatch always produces the three errors shown above.

`theme` and `version` are "missing" because they're really down inside `properties`, where
Python mode isn't looking. And `type` came back as `'Feature'`, the envelope's type,
which shows the mismatch. **If you ever see `input_value='Feature'` in a validation error,
you passed GeoJSON to a Python-mode call.**

For flat data, such as a Parquet row, a DuckDB result, or a dict of columns, `model_validate` is
the right call:

```python
row = {
    "id": "0e8abfe5-a7f3-4e8e-b6f0-db1fb0bb5b0c",
    "theme": "buildings",
    "type": "building",
    "version": 6,
    "geometry": "POLYGON ((-73.9864839 40.7485145, -73.9865012 40.748491, -73.9851602 40.7479255, -73.9848166 40.7483931, -73.9861574 40.7489585, -73.9863252 40.7487301, -73.9863554 40.748689, -73.9864839 40.7485145))",
    "height": 443.2,
    "class": "office",
}
flat_building = Building.model_validate(row)
```

In a flat row, `geometry` can be WKT text, as here, or WKB bytes, which is how Parquet
stores it.

## Reading fields

Model attributes are plain Python. Enums come back as enum members, geometry as a
`Geometry` wrapper around Shapely:

```python
building.height  # 443.2
building.class_  # <BuildingClass.OFFICE: 'office'>
building.class_.value  # 'office'
building.num_floors  # 102
type(building.geometry)  # <class 'overture.schema.system.geometric.geom.Geometry'>
```

## Writing data back out

Some field names are Python keywords, so the model attribute differs from the name in the
data: `class_` on the model, `class` in the data. **`model_dump()` uses attribute names by
default**, which produces output that won't validate back. The examples here
use the Empire State Building, and the second one fails on purpose:

```python
import json
from overture.schema.buildings import Building

building = Building.model_validate_json(
    open("guides/examples/buildings/empire-state-building.json").read()
)

d = building.model_dump(mode="json")
sorted(d["properties"])
# ['class_', 'facade_color', 'facade_material', 'has_parts', ...]   ← 'class_', not 'class'

Building.model_validate(building.model_dump(mode="python"))
# ValidationError: invalid extra field name: class_
```

The validator rejects `class_` because the data has no field by that name.

With `by_alias=True` both round-trips work:

```python
geojson = building.model_dump(mode="json", by_alias=True, exclude_none=True)
sorted(geojson["properties"])
# ['class', 'has_parts', 'height', 'is_underground', 'names', 'num_floors', ...]

Building.model_validate_json(json.dumps(geojson))  # OK
Building.model_validate(
    building.model_dump(mode="python", by_alias=True, exclude_none=True)
)  # OK
```

Same for `model_dump_json()`:

```python
'"class":' in building.model_dump_json()  # False  ← emits "class_"
'"class":' in building.model_dump_json(by_alias=True)  # True
```

**Rule of thumb: `by_alias=True` on every dump, unless you specifically want Python
attribute names.** `exclude_none=True` is usually what you want too. Otherwise you get
every unset optional field as an explicit `null`.

## Working with `Segment` and other unions

`Segment` is a [discriminated union](glossary.md#discriminated-union) over `RoadSegment`, `RailSegment`, and
`WaterSegment`, not a model class. It has no `model_validate`:

```python
from overture.schema.transportation import Segment

type(Segment)  # <class 'typing._AnnotatedAlias'>
Segment.model_validate({...})
# AttributeError: model_validate
```

Wrap it in a `TypeAdapter`:

```python
from pydantic import TypeAdapter
from overture.schema.transportation import Segment

segments = TypeAdapter(Segment)

seg = segments.validate_json(
    open("guides/examples/transportation/west-34th-street.json").read()
)
type(seg).__name__  # 'RoadSegment'
seg.names.primary  # 'West 34th Street'
```

`segments.validate_json()` reads GeoJSON. For flat data, such as a row read from Parquet,
use `segments.validate_python()`. This example writes the same segment out as a flat dict,
then validates it again:

```python
flat = seg.model_dump(mode="python", by_alias=True, exclude_none=True)
type(segments.validate_python(flat)).__name__  # 'RoadSegment'
```

The flat data has to be a segment. `validate_python()` reads `subtype` to choose between
`RoadSegment`, `RailSegment`, and `WaterSegment`, so data without it fails with
`Unable to extract tag using discriminator`.

Build the `TypeAdapter` once and reuse it; construction is the expensive part.

`RoadSegment`, `RailSegment`, and `WaterSegment` are ordinary model classes. If you know
which kind of segment you have, call its class directly:

```python
from overture.schema.transportation import RoadSegment

road = RoadSegment.model_validate_json(
    open("guides/examples/transportation/west-34th-street.json").read()
)
road.class_.value  # 'primary'
```

## Installing only some themes

When you build your own application on the Overture schema, it doesn't need every theme.
In [Getting started with the schema](getting-started-with-the-schema.md#install-from-pypi) you installed the metapackage, which includes all six. Your application
can depend on only the **theme packages it uses**. Create a new project for it in its own
directory. If you create it inside `my-overture-project`, `uv` treats it as part of that
project:

```bash
uv init myapp
cd myapp
uv add overture-schema-theme-buildings overture-schema-cli
uv run python -c "from overture.schema.buildings import Building; print(Building.__name__)"
```
```
Building
```

`uv add` records both packages in `myapp/pyproject.toml`:

```toml
dependencies = [
    "overture-schema-cli>=2.0.0",
    "overture-schema-theme-buildings>=2.0.0",
]
```

If you use `pip`, install the same two packages and list them in your requirements file:

```bash
pip install overture-schema-theme-buildings overture-schema-cli
```

In the `myapp` project, only the buildings package is installed, so `list-types` shows
only its two feature types:

```bash
uv run overture-schema list-types
```
```
building       feature  overture  overture:theme=buildings
building_part  feature  overture  overture:theme=buildings
```

This is the same command you ran in [Check the install](getting-started-with-the-schema.md#check-the-install), where it
listed 15 types. Here it lists
two because only the buildings package is installed. You don't configure this. Each theme
package registers its feature types through entry points, and the tools find the types in
whatever packages are installed.

You can use the same mechanism to add your own feature types. If you install a package
that registers its own models, its types appear in `list-types`, you can validate data
against them with the same commands, and they appear in generated docs alongside
Overture's. See [Register your own feature types](writing-models.md#package-and-register-your-models).

## Building a CLI on the models

To build your own command-line tool on the models, don't hardcode a list of feature types.
Find the installed types with `discover_models()`, and give your command the same `--tag`,
`--filter`, and `--exclude` options that `overture-schema` has. Your tool then works with
new themes and third-party extensions without any changes. For a step-by-step example,
follow [Building a command-line tool on the models](building-a-command-line-tool.md).

## Next steps

- [Validating data](validating-data.md)
- [Building a command-line tool on the models](building-a-command-line-tool.md)
- [Writing models](writing-models.md)
- [Concepts](concepts.md#the-geojson-envelope), for why GeoJSON puts most fields under
  `properties`
- [Troubleshooting](troubleshooting.md)
