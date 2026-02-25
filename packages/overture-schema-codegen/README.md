# Overture Schema Codegen

Code generator that produces documentation and code from Pydantic models.

## Installation

```bash
pip install overture-schema-codegen
```

## Usage

```python
from overture.schema.codegen import analyze_type, TypeInfo, TypeKind

# Analyze a type annotation
info = analyze_type(str)
assert info.base_type == "str"
assert info.kind == TypeKind.PRIMITIVE
```
