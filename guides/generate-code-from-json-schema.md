# Generate code from the JSON Schema

Use this page to generate types for another language from the Overture JSON Schema, so a
program in that language can read Overture features without the Overture Python packages.
The examples use the JSON Schema for buildings and the Empire State Building sample file.

## Before you start

You need the `overture-schema` command. To install it, see
[Install from PyPI](https://github.com/OvertureMaps/schema/blob/main/guides/getting-started-with-the-schema.md#install-from-pypi).
Download the sample file into your project, at the same path the schema repository uses:

```bash
curl -sSf --create-dirs -o guide-examples/buildings/empire-state-building.json \
  https://raw.githubusercontent.com/OvertureMaps/schema/main/guide-examples/buildings/empire-state-building.json
```

Each example starts by generating the JSON Schema for buildings:

```bash
uv run overture-schema json-schema --type building > building.schema.json
```

## Python with datamodel-code-generator

```bash
uv run overture-schema json-schema --type building > building.schema.json

uvx --python 3.12 --from datamodel-code-generator datamodel-codegen \
  --input building.schema.json \
  --input-file-type jsonschema \
  --formatters builtin \
  --output building_models.py
```

The generator reads the JSON Schema and writes Python classes to `building_models.py`.
They're ordinary Pydantic models, and they don't import any Overture package. Use them in
a program that needs to read Overture buildings without installing the Overture packages.
The `--python 3.12` and `--formatters builtin` options stop two warnings the generator
prints otherwise.

The generated `Building` class follows the GeoJSON form the JSON Schema describes, with
the other fields under `properties`:

```python
class Building(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    bbox: list[float] | None = Field(...)
    geometry: Geometry | Geometry1 = Field(...)
    id: constr(pattern=r"^\S+$", min_length=1) = Field(...)
    properties: Properties
    type: Literal["Feature"]
```

You can load a GeoJSON feature with it the usual Pydantic way:

```python
from building_models import Building

b = Building.model_validate_json(
    open("guide-examples/buildings/empire-state-building.json").read()
)
b.properties.height  # 443.2
```

## TypeScript with quicktype

```bash
npx -y quicktype --src-lang schema --lang typescript \
  -o Building.ts building.schema.json
```

quicktype writes `Building.ts`, with the schema's descriptions as JSDoc comments:

```typescript
/**
 * Buildings are man-made structures with roofs that exist permanently in one place.
 * ...
 */
export interface Building {
    /**
     * An optional bounding box for the feature
     */
    bbox?: [number, number, number, number, ...number[]];
    /**
     * The building's footprint or roofprint (if traced from aerial/satellite imagery).
     */
    geometry: Geometry;
    ...
```

> [!WARNING]
> quicktype ignores the JSON Schema keyword `patternProperties`, which the schema uses for
> `names.common`, a map from language codes to names. As a result, the generated
> `Convert.toBuilding()` rejects any building with common names, including the Empire
> State Building. The generated types are still correct, so you can parse with
> `JSON.parse()` and use the `Building` type:
>
> ```typescript
> import { readFileSync } from "node:fs";
> import type { Building } from "./Building";
>
> const building: Building = JSON.parse(
>   readFileSync("guide-examples/buildings/empire-state-building.json", "utf8")
> );
> console.log(building.properties.height);  // 443.2
> ```
>
> To run that, save it as `try-building.ts` and run `npx -y tsx try-building.ts`.

## Rust with typify

[`typify`](https://github.com/oxidecomputer/typify) has the same problem as quicktype
with `names.common`. To work around it, rewrite `patternProperties` as an ordinary map in
a copy of the JSON Schema, then generate Rust types from the copy. The first command
downloads a script that does the rewrite:

```bash
curl -sSfO https://raw.githubusercontent.com/OvertureMaps/schema/main/guide-examples/scripts/fix_pattern_properties.py
cargo install cargo-typify
uv run python fix_pattern_properties.py building.schema.json building.rust.schema.json
cargo typify building.rust.schema.json -o building_types.rs
```

To use the generated types, add them to a Rust project with the crates they need:

```bash
cargo new building-demo
cd building-demo
cargo add serde --features derive
cargo add serde_json regress
cargo add chrono --features serde
mv ../building_types.rs src/
```

Then replace `src/main.rs` with:

```rust
mod building_types;

use building_types::Building;

fn main() {
    let text = std::fs::read_to_string(
        "../guide-examples/buildings/empire-state-building.json",
    )
    .unwrap();
    let building: Building = serde_json::from_str(&text).unwrap();
    println!("{:?}", building.properties.height);
}
```

`cargo run` prints `Some(443.2)`.

> [!WARNING]
> The generated Rust types check structure and types, not every rule in the schema. They
> accept a negative `height`, for example, and after the rewrite they accept any string
> as a language code in `names.common`. Validate with the Overture packages when you need
> every rule checked.

## Other languages and generators

quicktype also targets Go, Rust, Java, Kotlin, Swift, C#, and others from the same input.
Anything that reads JSON Schema works the same way, including OpenAPI toolchains,
`go-jsonschema`, `schemars`, and `jsonschema2pojo`.

The tradeoff: you get types and structural validation, but not the semantic layer.
Cross-field model constraints (`@require_any_of`, `@radio_group`) do translate into JSON
Schema `if`/`then`/`anyOf` constructs, but domain-specific error messages and the
NewType vocabulary flatten out.
