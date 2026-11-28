# Adding a codegen target

Use this page to add an output format to `overture-codegen`, such as Arrow schemas, Avro,
Go structs or protobuf. Write a renderer for the code generator instead of parsing the
generated JSON Schema. The code generator gives your renderer what JSON Schema loses:
NewType names, where each constraint comes from, and the structure of discriminated
unions.

The code generator has four layers, and each layer imports only from the layers below it:

```
Rendering        →  output formatting, all presentation decisions
Output Layout    →  what to generate, where it goes, how outputs link
Extraction       →  FieldShape, FieldSpec, RecordSpec, UnionSpec, EnumSpec
Discovery        →  discover_models()
```

The extraction layer is the same for every target, so a new target needs a new renderer
but no new extraction code. Start with `extract_model()`:

```python
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.buildings import Building

spec = extract_model(Building)
spec.name  # 'Building'
spec.description  # the class docstring
spec.constraints  # model-level constraints

for f in spec.fields[:6]:
    print(f"{f.name:12} required={f.is_required!s:5} {type(f.shape).__name__}")
```

```
id           required=True  NewTypeShape
bbox         required=False Primitive
geometry     required=True  Primitive
theme        required=True  LiteralScalar
type         required=True  LiteralScalar
version      required=True  NewTypeShape
```

A `FieldSpec` has a `name`, a `shape`, a `description`, `is_required` and `is_optional`.
The `shape` is a `FieldShape` tree, made of `NewTypeShape`, `Primitive`, `LiteralScalar`,
`ModelRef`, `UnionRef` and container types, with nested models and unions already
resolved. Each constraint records its source, so you can tell which NewType contributed
which bound:

```python
from overture.schema.codegen.extraction.type_analyzer import analyze_type
from overture.schema.common.feature import FeatureVersion

shape, is_nullable, description = analyze_type(FeatureVersion)
# shape → NewTypeShape(name='FeatureVersion', inner=Primitive(base_type='int32',
#           constraints=(ConstraintSource(source_name='FeatureVersion', constraint=Ge(ge=0)), ...)))
```

`analyze_type()` returns three values: the `FieldShape`, whether the field accepts `None`,
and the first description it found while unwrapping the type.

To add the new format:

1. Add a column to `TypeMapping` in `extraction/type_registry.py`, so type names resolve.
2. Write a pipeline module that reads `ModelSpec` trees, and a renderer.
3. Register the format in `cli.py`.

For the architecture, the data flow and the extension points, see `design.md`. For a
module-by-module trace of `Segment` through the pipeline, see `walkthrough.md`.
