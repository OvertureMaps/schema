# Building a command-line tool on the models

Use this tutorial to build a command-line tool on the Overture schema models. You'll build
`explain_sources`, a command that says where each part of a feature's data came from. Along
the way, you'll read a model's fields in Python, validate any installed feature type, and
give your command the same `--tag`, `--filter`, and `--exclude` options that
`overture-schema` has.

Finish [Getting started with the schema](getting-started-with-the-schema.md) first. For
background on what the `sources` field records, read [Sources](concepts.md#sources).

## Before you start

You need the five sample files from
[Get the sample files](getting-started-with-the-schema.md#get-the-sample-files). The
command uses [Click](https://click.palletsprojects.com/), which the `overture-schema`
metapackage already installs. Run every command from your project directory, and keep your
work in one file, `explain_sources.py`.

## Print a feature's sources

Start with one feature: the Starbucks Reserve in the Empire State Building. Save this as
`explain_sources.py`:

```python
from overture.schema.places import Place

with open("guides/examples/places/starbucks-reserve-empire-state-building.json") as f:
    place = Place.model_validate_json(f.read())

for source in place.sources:
    print(repr(source.property), source.dataset, source.record_id)
```

Run it:

```bash
uv run python explain_sources.py
```
```
'' Uberall 175212156
'/properties/confidence' Overture None
'/properties/operating_status' Overture-signals 44846d58-7c5c-44a9-9066-58be5441b702
```

The place has three sources. Each line shows the source's `property`, its `dataset`, and
its `record_id`. The empty `property` means the source covers the whole feature, except
the parts that have a source of their own. The other two sources cover one field each:
Overture calculated the place's `confidence`, so that source has no record ID, and
Overture's operating-status signals supplied its `operating_status`.

## Say which part each source covers

The pointers in `property` are hard to read, and nothing checks that the feature has the
field a pointer names. Replace the contents of `explain_sources.py` with this version,
which adds two functions:

```python
from overture.schema.places import Place


def field_path(pointer, flat):
    """Turn a source's JSON Pointer into a field path, and check the feature has it."""
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    if parts[:1] == ["properties"]:
        parts = parts[1:]  # GeoJSON form: /properties/height means the field height
    value = flat
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return ".".join(parts) + " (not in this feature)"
    return ".".join(parts)


def describe(source, flat, others):
    """One line saying which part of the feature a source covers, and the source."""
    if source.property:
        part = field_path(source.property, flat)
    else:
        part = "everything else" if others else "the whole feature"
    origin = " ".join(x for x in (source.dataset, source.record_id) if x)
    return f"{part}: {origin}"


with open("guides/examples/places/starbucks-reserve-empire-state-building.json") as f:
    place = Place.model_validate_json(f.read())

flat = place.model_dump(mode="python", by_alias=True, exclude_none=True)
others = any(s.property != "" for s in place.sources)
for source in place.sources:
    print(describe(source, flat, others))
```

`field_path()` turns a pointer such as `/properties/confidence` into the field name
`confidence`. It accepts pointers in both forms that Overture data uses, and it marks any
field the feature doesn't have. It looks the field up in the flat form of the feature,
which you get from `model_dump(mode="python")`. `describe()` writes one line for each
source, and it says "everything else" for the empty pointer when other sources cover
single fields.

Run it again:

```bash
uv run python explain_sources.py
```
```
everything else: Uberall 175212156
confidence: Overture
operating_status: Overture-signals 44846d58-7c5c-44a9-9066-58be5441b702
```

## Read any feature type

So far the script reads only places, because it calls `Place.model_validate_json()`. To
read any feature, use `validate_json()` from `overture.schema.validation`. It checks the
data against every installed feature type and returns a model of the type that matched.
Replace the contents of `explain_sources.py` with this version. It takes file names on the
command line, and it adds three things to `describe()`:

- the part of a segment a source covers, from its `between` value
- the date the source record was last updated
- the source's confidence score, when it has one

```python
import sys

from overture.schema.validation import validate_json


def field_path(pointer, flat):
    """Turn a source's JSON Pointer into a field path, and check the feature has it."""
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    if parts[:1] == ["properties"]:
        parts = parts[1:]  # GeoJSON form: /properties/height means the field height
    value = flat
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return ".".join(parts) + " (not in this feature)"
    return ".".join(parts)


def describe(source, flat, others):
    """One line saying which part of the feature a source covers, and the source."""
    if source.property:
        part = field_path(source.property, flat)
    else:
        part = "everything else" if others else "the whole feature"
    if source.between:
        start, end = (round(x * 100, 1) for x in source.between)
        span = f"from {start:g}% to {end:g}% of its length"
        part = span if not source.property else f"{part}, {span}"
    origin = " ".join(x for x in (source.dataset, source.record_id) if x)
    details = [f"updated {source.update_time:%Y-%m-%d}"] if source.update_time else []
    if source.confidence is not None:
        details.append(f"confidence {source.confidence}")
    return f"{part}: {origin}" + (f" ({', '.join(details)})" if details else "")


for path in sys.argv[1:]:
    with open(path) as f:
        feature = validate_json(f.read())
    flat = feature.model_dump(mode="python", by_alias=True, exclude_none=True)
    others = any(s.property != "" for s in feature.sources)
    names = getattr(feature, "names", None)
    name = f" ({names.primary})" if names else ""
    print(f"{feature.type} {feature.id}{name}")
    for source in feature.sources:
        print("  " + describe(source, flat, others))
```

Run it on the Empire State Building and on West 34th Street:

```bash
uv run python explain_sources.py \
  guides/examples/buildings/empire-state-building.json \
  guides/examples/transportation/west-34th-street.json
```
```
building 0e8abfe5-a7f3-4e8e-b6f0-db1fb0bb5b0c (Empire State Building)
  the whole feature: OpenStreetMap w34633854@78 (updated 2026-09-07)
segment e0fe7f44-2ba6-44bf-ae1e-797e39a04485 (West 34th Street)
  from 0% to 12.5% of its length: OpenStreetMap w1088325196@27 (updated 2026-05-02)
  from 12.5% to 100% of its length: OpenStreetMap w5670600@68 (updated 2026-08-27)
```

The building comes from one OpenStreetMap way. West 34th Street comes from two, joined
12.5% of the way along the segment.

## Turn the script into a command

With Click, you get a `--help` page and checks on the arguments, and you can add options
later. Replace the contents of `explain_sources.py` with this version, which turns the loop
at the end into a Click command. It also reads a `FeatureCollection`, so one file can hold
many features:

```python
import json

import click

from overture.schema.validation import validate_json


def field_path(pointer, flat):
    """Turn a source's JSON Pointer into a field path, and check the feature has it."""
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    if parts[:1] == ["properties"]:
        parts = parts[1:]  # GeoJSON form: /properties/height means the field height
    value = flat
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return ".".join(parts) + " (not in this feature)"
    return ".".join(parts)


def describe(source, flat, others):
    """One line saying which part of the feature a source covers, and the source."""
    if source.property:
        part = field_path(source.property, flat)
    else:
        part = "everything else" if others else "the whole feature"
    if source.between:
        start, end = (round(x * 100, 1) for x in source.between)
        span = f"from {start:g}% to {end:g}% of its length"
        part = span if not source.property else f"{part}, {span}"
    origin = " ".join(x for x in (source.dataset, source.record_id) if x)
    details = [f"updated {source.update_time:%Y-%m-%d}"] if source.update_time else []
    if source.confidence is not None:
        details.append(f"confidence {source.confidence}")
    return f"{part}: {origin}" + (f" ({', '.join(details)})" if details else "")


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True, dir_okay=False))
def explain_sources(paths):
    """Say where each part of each feature in the GeoJSON files came from."""
    items = []
    for path in paths:
        with open(path) as f:
            data = json.load(f)
        items += data["features"] if data.get("type") == "FeatureCollection" else [data]
    for item in items:
        feature = validate_json(json.dumps(item))
        flat = feature.model_dump(mode="python", by_alias=True, exclude_none=True)
        others = any(s.property != "" for s in feature.sources)
        names = getattr(feature, "names", None)
        name = f" ({names.primary})" if names else ""
        click.echo(f"{feature.type} {feature.id}{name}")
        for source in feature.sources:
            click.echo("  " + describe(source, flat, others))


if __name__ == "__main__":
    explain_sources()
```

Run it on all four sample features:

```bash
uv run python explain_sources.py \
  guides/examples/buildings/empire-state-building.json \
  guides/examples/places/starbucks-reserve-empire-state-building.json \
  guides/examples/divisions/manhattan.json \
  guides/examples/transportation/west-34th-street.json
```
```
building 0e8abfe5-a7f3-4e8e-b6f0-db1fb0bb5b0c (Empire State Building)
  the whole feature: OpenStreetMap w34633854@78 (updated 2026-09-07)
place 3e5a04fb-d588-4266-95fe-658f2f324a9b (Starbucks Reserve - Empire State Building)
  everything else: Uberall 175212156 (updated 2026-11-09, confidence 0.95)
  confidence: Overture (updated 2026-11-11)
  operating_status: Overture-signals 44846d58-7c5c-44a9-9066-58be5441b702 (updated 2026-07-20, confidence 1.0)
division 84d8a97e-4624-43a4-9c7f-5c853ac90703 (Manhattan)
  everything else: OpenStreetMap r8398124@51 (updated 2026-11-02)
  geometry: OpenStreetMap n357644127@48 (updated 2026-01-30)
segment e0fe7f44-2ba6-44bf-ae1e-797e39a04485 (West 34th Street)
  from 0% to 12.5% of its length: OpenStreetMap w1088325196@27 (updated 2026-05-02)
  from 12.5% to 100% of its length: OpenStreetMap w5670600@68 (updated 2026-08-27)
```

Manhattan comes from an OpenStreetMap relation, except its point geometry, which comes
from an OpenStreetMap node.

## Add the tag options

`overture-schema` lets you choose feature types with `--tag`, `--filter`, and `--exclude`.
Give your command the same options with the `@tag_selection_options` decorator from
`overture.schema.cli`. Then pass your selection to `resolve_types()`, which builds a union
of the feature types you chose, the same way `overture-schema validate` does. A feature
that isn't one of those types fails validation, so this version skips it with a short
message. Replace the contents of `explain_sources.py` with it:

```python
import json

import click
from pydantic import TypeAdapter, ValidationError

from overture.schema.cli import resolve_types
from overture.schema.cli.tag_options import build_selector, tag_selection_options


def field_path(pointer, flat):
    """Turn a source's JSON Pointer into a field path, and check the feature has it."""
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    if parts[:1] == ["properties"]:
        parts = parts[1:]  # GeoJSON form: /properties/height means the field height
    value = flat
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return ".".join(parts) + " (not in this feature)"
    return ".".join(parts)


def describe(source, flat, others):
    """One line saying which part of the feature a source covers, and the source."""
    if source.property:
        part = field_path(source.property, flat)
    else:
        part = "everything else" if others else "the whole feature"
    if source.between:
        start, end = (round(x * 100, 1) for x in source.between)
        span = f"from {start:g}% to {end:g}% of its length"
        part = span if not source.property else f"{part}, {span}"
    origin = " ".join(x for x in (source.dataset, source.record_id) if x)
    details = [f"updated {source.update_time:%Y-%m-%d}"] if source.update_time else []
    if source.confidence is not None:
        details.append(f"confidence {source.confidence}")
    return f"{part}: {origin}" + (f" ({', '.join(details)})" if details else "")


@click.command()
@tag_selection_options
@click.argument("paths", nargs=-1, type=click.Path(exists=True, dir_okay=False))
def explain_sources(tags, filters, excludes, paths):
    """Say where each part of each feature in the GeoJSON files came from."""
    adapter = TypeAdapter(resolve_types(build_selector(tags, filters, excludes)))
    items = []
    for path in paths:
        with open(path) as f:
            data = json.load(f)
        items += data["features"] if data.get("type") == "FeatureCollection" else [data]
    for item in items:
        try:
            feature = adapter.validate_json(json.dumps(item))
        except ValidationError as error:
            click.echo(
                f"skipped {item.get('id')}: {error.error_count()} validation errors"
            )
            continue
        flat = feature.model_dump(mode="python", by_alias=True, exclude_none=True)
        others = any(s.property != "" for s in feature.sources)
        names = getattr(feature, "names", None)
        name = f" ({names.primary})" if names else ""
        click.echo(f"{feature.type} {feature.id}{name}")
        for source in feature.sources:
            click.echo("  " + describe(source, flat, others))


if __name__ == "__main__":
    explain_sources()
```

Run it on the Starbucks Reserve and on Manhattan, and select only places:

```bash
uv run python explain_sources.py --tag overture:theme=places \
  guides/examples/places/starbucks-reserve-empire-state-building.json \
  guides/examples/divisions/manhattan.json
```
```
place 3e5a04fb-d588-4266-95fe-658f2f324a9b (Starbucks Reserve - Empire State Building)
  everything else: Uberall 175212156 (updated 2026-11-09, confidence 0.95)
  confidence: Overture (updated 2026-11-11)
  operating_status: Overture-signals 44846d58-7c5c-44a9-9066-58be5441b702 (updated 2026-07-20, confidence 1.0)
skipped 84d8a97e-4624-43a4-9c7f-5c853ac90703: 2 validation errors
```

Run `uv run python explain_sources.py --help` to see all the options. Because the command
finds feature types through discovery, it works with any theme package you install,
including feature types of your own.

## Next steps

In this tutorial, you built a command that explains a feature's sources. You read a
model's fields and turned its JSON Pointers into field names. Then you validated any
installed feature type, and gave the command the same tag options as `overture-schema`.

`overture.schema.cli` also has `load_input`, `perform_validation`,
`handle_validation_error`, and `handle_generic_error`. You can use them to load input and
show errors the way `overture-schema validate` does.

Where you go next depends on what you're building:

- To learn more about sources, the GeoJSON envelope, and tags, read
  [Concepts](concepts.md).
- To load, change, and write features in your own code, read
  [Working with features in Python](working-with-features.md).
- To define feature types of your own, so your command and the Overture tools work with
  them, read [Writing models](writing-models.md).
