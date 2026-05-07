"""Shared fill-value table for non-string scalar Spark categories.

Maps each SparkCategory that requires an explicit fill value to a
`(source_literal, runtime_value)` pair. The source literal is a valid
Python expression string; the runtime value is the corresponding Python
object.

Consumers
---------
- `constraint_dispatch._needs_explicit_fill`: category in PRIMITIVE_FILL_TABLE
- `test_renderer._fill_value_literal`: PRIMITIVE_FILL_TABLE[category][0]
- `test_data.base_row._primitive_default`: PRIMITIVE_FILL_TABLE[category][1]

Adding a new numeric category here automatically wires it into all three.
"""

from ..extraction.type_registry import SparkCategory

PRIMITIVE_FILL_TABLE: dict[SparkCategory, tuple[str, object]] = {
    "int": ("0", 0),
    "float": ("0.0", 0.0),
    "bool": ("False", False),
}
