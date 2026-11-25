"""Rewrite JSON Schema `patternProperties` as `additionalProperties`.

Some code generators, including quicktype and typify, ignore `patternProperties`.
The Overture schema uses it for `names.common`, a map from language codes to names,
so those generators produce an empty type that rejects real data. This script writes
a copy of the schema where each single-pattern `patternProperties` becomes an ordinary
map. The copy no longer checks that the keys are valid language codes.

Usage: python fix_pattern_properties.py INPUT.json OUTPUT.json
"""

import json
import sys


def fix(node):
    if isinstance(node, dict):
        pattern_properties = node.get("patternProperties")
        if pattern_properties and len(pattern_properties) == 1:
            (value_schema,) = pattern_properties.values()
            node.pop("patternProperties")
            node["additionalProperties"] = value_schema
        for value in node.values():
            fix(value)
    elif isinstance(node, list):
        for value in node:
            fix(value)
    return node


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        schema = json.load(f)
    with open(sys.argv[2], "w") as f:
        json.dump(fix(schema), f, indent=2)
