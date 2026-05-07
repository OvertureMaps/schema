"""Test-data generation for the rendered PySpark conformance tests.

Three modules cover three flavors of data:

- `invalid_value`: constraint-violating values for triggering each check.
- `base_row`: minimal and fully populated valid rows.
- `scaffold`: sparse path scaffolds that supply the nested intermediates
  (optional structs, arrays) a check's field path requires.
"""
