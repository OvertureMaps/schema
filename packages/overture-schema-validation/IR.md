# Validation Rule IR Specification

Version: 1

## 1. Overview

The Overture validation system uses a three-layer architecture:

1. **Extractor** — reads Pydantic model definitions and emits validation rules in this IR format
2. **IR (this document)** — a portable, engine-agnostic YAML vocabulary describing validation rules
3. **Backend adapters** — compile IR rules into native queries for DuckDB, Spark, Polars, or other engines

This document is the authoritative reference for the IR layer. It defines the YAML schema, the closed check vocabulary, conditional evaluation, and output structure.

---

## 2. Root Structure

A validation spec is a versioned YAML document containing one or more dataset definitions:

```yaml
version: "1"

datasets:
  - name: Building
    source_model: overture.schema.buildings.building.Building
    id_column: id
    rules:
      - ...
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `version` | string | yes | Schema version of this IR document |
| `datasets` | list of DatasetSpec | yes | One entry per dataset to validate |

### DatasetSpec

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Human-readable dataset name |
| `source_model` | string | no | null | Fully-qualified Pydantic class for traceability |
| `id_column` | string | no | `"id"` | Column used to identify violating rows |
| `rules` | list of Rule | yes | — | Validation rules for this dataset |

---

## 3. Rule Schema

Each rule specifies a single validation check on one or more columns.

```yaml
- name: building.height.positive
  column: height
  check: gt
  value: 0
  severity: error
  description: "Height must be greater than 0"
```

### Rule Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Unique dot-path identifier |
| `column` | string | conditional | Target column (dot notation for nested) |
| `columns` | list of string | conditional | Target columns (multi-field checks only) |
| `check` | CheckType | yes | One of the 22 check types |
| `value` | scalar, list, or null | conditional | Check parameter |
| `other_column` | string | conditional | Second column (column comparison checks) |
| `list_columns` | list of string | no | Ordered list-boundary columns for nested list iteration |
| `when` | Condition | no | Predicate guard |
| `severity` | `error` or `warning` | yes | Severity level |
| `description` | string | no | Human-readable explanation |

### Structural Constraints

| Field | Required when | Forbidden when |
|---|---|---|
| `column` | any check except `exactly_one_of`, `any_of` | `columns` is set |
| `columns` | `exactly_one_of`, `any_of` | `column` is set |
| `value` | all scalar/list checks | `not_null`, `is_null`, `unique`, multi-field checks |
| `other_column` | `column_lt`, `column_lte`, `column_eq` | all other checks |
| `list_columns` | never (optional) | check is `exactly_one_of` or `any_of` |

### Nested Column Access

Use dot notation to reach into Parquet structs:

```yaml
column: cartography.prominence    # struct field
column: names.primary             # struct field
```

### Condition

A `when` clause is a single predicate. No nesting allowed.

| Field | Type | Required | Description |
|---|---|---|---|
| `column` | string | yes | Column to evaluate |
| `check` | CheckType | yes | Restricted to single-column, non-aggregate checks |
| `value` | scalar, list, or null | conditional | Check parameter |

---

## 4. Check Vocabulary

The IR defines a closed set of 22 check types. All backend adapters must support every check type.

### 4.1 Scalar Comparison Checks

All take a single scalar `value`.

#### `gt` — greater than

Violation: `col <= value`

```yaml
- name: building.height.positive
  column: height
  check: gt
  value: 0
  severity: error
```

#### `gte` — greater than or equal

Violation: `col < value`

```yaml
- name: overture.version.non_negative
  column: version
  check: gte
  value: 0
  severity: error
```

#### `lt` — less than

Violation: `col >= value`

```yaml
- name: building.roof_direction.upper
  column: roof_direction
  check: lt
  value: 360
  severity: error
```

#### `lte` — less than or equal

Violation: `col > value`

```yaml
- name: cartography.min_zoom.upper
  column: cartography.min_zoom
  check: lte
  value: 23
  severity: error
```

#### `eq` — equals

Violation: `col != value`

```yaml
- name: road_segment.subtype.literal
  column: subtype
  check: eq
  value: road
  severity: error
```

#### `neq` — not equals

Violation: `col == value`

```yaml
- name: example.status.not_deleted
  column: status
  check: neq
  value: deleted
  severity: warning
```

### 4.2 Range Check

#### `between` — inclusive range

Value is a two-element list `[min, max]`.

Violation: `col < min OR col > max`

```yaml
- name: place.confidence.range
  column: confidence
  check: between
  value: [0.0, 1.0]
  severity: error
```

### 4.3 Set Membership Checks

#### `in` — value must be in set

Value is a list of allowed values.

Violation: `col NOT IN (...)`

```yaml
- name: water.subtype.valid
  column: subtype
  check: in
  value: [water, stream, river]
  severity: error
```

With `list_columns`, every list element must be in the set:

```yaml
- name: road_flag_rule.values.items_valid
  column: values
  check: in
  value: [is_link, is_toll, is_bridge]
  list_columns: [values]
  severity: error
```

#### `not_in` — value must not be in set

Violation: `col IN (...)`

```yaml
- name: example.status.excluded
  column: status
  check: not_in
  value: [banned, suspended]
  severity: error
```

### 4.4 Null Checks

#### `not_null` — column must not be null

Violation: `col IS NULL`

```yaml
- name: overture.id.required
  column: id
  check: not_null
  severity: error
```

Conditional example (required-if):

```yaml
- name: division.parent_id.required_when_not_country
  column: parent_division_id
  check: not_null
  severity: error
  when:
    column: subtype
    check: neq
    value: country
```

#### `is_null` — column must be null

Violation: `col IS NOT NULL`

```yaml
- name: division.parent_id.forbidden_when_country
  column: parent_division_id
  check: is_null
  severity: error
  when:
    column: subtype
    check: eq
    value: country
```

### 4.5 Uniqueness Check

#### `unique` — no duplicate values

On a **scalar column**: aggregate check across all rows.

```yaml
- name: overture.id.unique
  column: id
  check: unique
  severity: error
```

On a **list column**: per-row check within each row's list.

```yaml
- name: place.websites.items_unique
  column: websites
  check: unique
  severity: error
```

### 4.6 Length Checks

Apply to strings (character length) or lists (element count).

#### `min_length`

Violation: `LENGTH(col) < value` (strings) or `ARRAY_LENGTH(col) < value` (lists)

```yaml
- name: overture.id.min_length
  column: id
  check: min_length
  value: 1
  severity: error
```

#### `max_length`

Violation: `LENGTH(col) > value` (strings) or `ARRAY_LENGTH(col) > value` (lists)

```yaml
- name: address.levels.max_length
  column: address_levels
  check: max_length
  value: 5
  severity: error
```

### 4.7 Pattern Check

#### `pattern` — regex match

Violation: `NOT REGEXP_MATCHES(col, value)`

```yaml
- name: overture.id.no_whitespace
  column: id
  check: pattern
  value: '^\S+$'
  severity: error
```

With `list_columns`:

```yaml
- name: place.phones.item_format
  column: phones
  check: pattern
  value: '^\+\d{1,3}[\s\-\(\)0-9]+$'
  list_columns: [phones]
  severity: error
```

### 4.8 Type Check

#### `is_type` — column type/value assertion

Supported type names: `boolean`, `integer`, `float`, `string`, `date`, `datetime`

Violation: value exists but fails type cast/coercion check

```yaml
- name: water.is_salt.type
  column: is_salt
  check: is_type
  value: boolean
  severity: error
```

### 4.9 Column Comparison Checks

Compare two columns within the same row.

#### `column_lt` — column less than another column

Violation: `col >= other_column`

```yaml
- name: bbox.xmin_lt_xmax
  column: bbox.xmin
  check: column_lt
  other_column: bbox.xmax
  severity: error
```

#### `column_lte` — column less than or equal to another column

Violation: `col > other_column`

```yaml
- name: example.start_lte_end
  column: start_date
  check: column_lte
  other_column: end_date
  severity: error
```

#### `column_eq` — column equals another column

Violation: `col != other_column`

```yaml
- name: example.confirmed_matches_actual
  column: confirmed_count
  check: column_eq
  other_column: actual_count
  severity: warning
```

### 4.10 Geometry Type Check

#### `geometry_type` — restrict allowed geometry types

Value is a list of allowed GeoJSON geometry type strings.

Violation: geometry type not in allowed list

```yaml
- name: building.geometry.type
  column: geometry
  check: geometry_type
  value: [Polygon, MultiPolygon]
  severity: error
```

Backend hint: DuckDB spatial — `ST_GeometryType(geometry) NOT IN (...)`.

### 4.11 Multi-Field Checks

These use `columns` (list) instead of `column` (single).

#### `exactly_one_of` — exactly one column must be non-null

Violation: zero or more than one of the listed columns is non-null

```yaml
- name: division_area.land_or_territorial
  columns: [is_land, is_territorial]
  check: exactly_one_of
  severity: error
```

#### `any_of` — at least one column must be non-null

Violation: all listed columns are null

```yaml
- name: speed_limit.speed_present
  columns: [max_speed, min_speed]
  check: any_of
  severity: error
```

---

## 5. List Column Iteration (`list_columns`)

When `list_columns` is set, the backend must iterate through the specified list boundaries to evaluate the check on nested elements.

### Semantics

`list_columns` is an ordered list of column paths. Each entry is a column that is a `LIST(...)` type requiring iteration. The backend wraps the check in nested `list_filter` calls from outside in.

- If `column == list_columns[-1]`, the check targets **each element** of the innermost list
- Otherwise, the check targets a struct field accessed from the innermost lambda variable

### Example 1: Simple list

```yaml
- name: place.phones.item_format
  column: phones
  check: pattern
  value: '^\+\d{1,3}[\s\-\(\)0-9]+$'
  list_columns: [phones]
  severity: error
```

Here `column == list_columns[-1]`, so the pattern check applies to each element of the `phones` list.

### Example 2: List of structs

```yaml
- name: division.names.rules.value.not_null
  column: names.rules.value
  check: not_null
  list_columns: [names.rules]
  severity: error
```

Here `column != list_columns[-1]`, so the backend iterates over `names.rules` and checks the `value` field of each struct element.

### Example 3: Nested list in struct in list

```yaml
- name: division.names.rules.perspectives.countries.pattern
  column: names.rules.perspectives.countries
  check: pattern
  value: '^[A-Z]{2}$'
  list_columns: [names.rules, names.rules.perspectives.countries]
  severity: error
```

Here `column == list_columns[-1]`, so the backend generates nested `list_filter` calls — the outer one iterates `names.rules`, and the inner one iterates `perspectives.countries` within each struct, checking each country code element.

### Not allowed with

`list_columns` must not be set on multi-field checks (`exactly_one_of`, `any_of`).

---

## 6. Conditional Rules (`when`)

A `when` clause restricts when the rule is evaluated. Rows that **do not** satisfy the `when` condition are **skipped** (not violations).

### Allowed checks inside `when`

All single-column, non-aggregate checks: `gt`, `gte`, `lt`, `lte`, `eq`, `neq`, `between`, `in`, `not_in`, `not_null`, `is_null`, `pattern`, `is_type`.

### Not allowed inside `when`

`unique` (aggregate), `exactly_one_of`, `any_of` (multi-field), `column_*` (two-column), `geometry_type`.

### No nesting

A `when` clause cannot itself contain a `when`.

### Examples

Required-if pattern:

```yaml
- name: division.admin_level.required_for_country
  column: admin_level
  check: not_null
  severity: error
  when:
    column: subtype
    check: in
    value: [country, dependency, region]
```

Forbidden-if pattern:

```yaml
- name: division.parent_id.forbidden_when_country
  column: parent_division_id
  check: is_null
  severity: error
  when:
    column: subtype
    check: eq
    value: country
```

---

## 7. Multi-Field Checks

Multi-field checks use the `columns` field (a list of column names) instead of the single `column` field. They test relationships between multiple columns in the same row.

The `column` field must not be set when using multi-field checks.

See section 4.11 for `exactly_one_of` and `any_of`.

---

## 8. Output Structure

Backend adapters produce a `ValidationReport` after evaluating rules against a dataset.

### ValidationReport

| Field | Type | Description |
|---|---|---|
| `dataset` | string | Name of the dataset that was validated |
| `total_rows` | integer | Total number of rows in the dataset |
| `results` | list of RuleResult | One entry per evaluated rule |

### RuleResult

| Field | Type | Description |
|---|---|---|
| `rule_name` | string | Name of the rule (matches `Rule.name`) |
| `description` | string or null | Rule description |
| `violating_ids` | list | IDs of rows that violated the rule |
| `violation_count` | integer | Number of violations |
| `severity` | `error` or `warning` | Severity of the rule |

---

## 9. Complete Example — Building Dataset

```yaml
version: "1"

datasets:
  - name: Building
    source_model: overture.schema.buildings.building.Building
    id_column: id
    rules:
      - name: building.id.not_null
        column: id
        check: not_null
        severity: error
        description: "Feature ID is required"

      - name: building.id.min_length
        column: id
        check: min_length
        value: 1
        severity: error
        description: "Feature ID must be at least 1 character"

      - name: building.id.pattern
        column: id
        check: pattern
        value: '^\S+$'
        severity: error
        description: "Feature ID must not contain whitespace"

      - name: building.id.unique
        column: id
        check: unique
        severity: error
        description: "Feature IDs must be unique across dataset"

      - name: building.version.not_null
        column: version
        check: not_null
        severity: error
        description: "Version is required"

      - name: building.version.gte
        column: version
        check: gte
        value: 0
        severity: error
        description: "Version must be >= 0"

      - name: building.geometry.not_null
        column: geometry
        check: not_null
        severity: error
        description: "Geometry is required"

      - name: building.geometry.type
        column: geometry
        check: geometry_type
        value: [Polygon, MultiPolygon]
        severity: error
        description: "Building geometry must be Polygon or MultiPolygon"

      - name: building.names.primary.min_length
        column: names.primary
        check: min_length
        value: 1
        severity: error
        description: "Primary name must be at least 1 character"
        when:
          column: names
          check: not_null

      - name: building.names.primary.pattern
        column: names.primary
        check: pattern
        value: '^(\S.*)?\S$'
        severity: error
        description: "Primary name must not have leading/trailing whitespace"
        when:
          column: names
          check: not_null

      - name: building.cartography.prominence.range
        column: cartography.prominence
        check: between
        value: [1, 100]
        severity: error
        description: "Prominence must be between 1 and 100"

      - name: building.cartography.min_zoom.range
        column: cartography.min_zoom
        check: between
        value: [0, 23]
        severity: error
        description: "Min zoom must be between 0 and 23"

      - name: building.cartography.max_zoom.range
        column: cartography.max_zoom
        check: between
        value: [0, 23]
        severity: error
        description: "Max zoom must be between 0 and 23"

      - name: building.height.positive
        column: height
        check: gt
        value: 0
        severity: error
        description: "Height must be > 0"

      - name: building.num_floors.positive
        column: num_floors
        check: gt
        value: 0
        severity: error
        description: "Number of floors must be > 0"

      - name: building.roof_direction.lower
        column: roof_direction
        check: gte
        value: 0
        severity: error
        description: "Roof direction must be >= 0"

      - name: building.roof_direction.upper
        column: roof_direction
        check: lt
        value: 360
        severity: error
        description: "Roof direction must be < 360"

      - name: building.facade_color.pattern
        column: facade_color
        check: pattern
        value: '^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$'
        severity: error
        description: "Facade color must be a valid hex color code"

      - name: building.roof_shape.valid
        column: roof_shape
        check: in
        value: [dome, flat, gambrel, gabled, half_hipped, hipped, mansard, onion, pyramidal, round, saltbox, sawtooth, skillion, windmill]
        severity: error
        description: "Roof shape must be a valid RoofShape"

      - name: building.is_underground.type
        column: is_underground
        check: is_type
        value: boolean
        severity: error
        description: "is_underground must be a strict boolean"

      - name: building.subtype.valid
        column: subtype
        check: in
        value: [agricultural, civic, commercial, education, entertainment, industrial, medical, military, outbuilding, religious, residential, service, transportation]
        severity: error
        description: "Subtype must be a valid BuildingSubtype"

      - name: building.has_parts.type
        column: has_parts
        check: is_type
        value: boolean
        severity: error
        description: "has_parts must be a strict boolean"
```

---

## Appendix: Check Reference Table

| Check | Value type | `column` | `columns` | `other_column` | `list_columns` | Violation condition |
|---|---|---|---|---|---|---|
| `gt` | scalar | required | — | — | optional | `col <= value` |
| `gte` | scalar | required | — | — | optional | `col < value` |
| `lt` | scalar | required | — | — | optional | `col >= value` |
| `lte` | scalar | required | — | — | optional | `col > value` |
| `eq` | scalar | required | — | — | optional | `col != value` |
| `neq` | scalar | required | — | — | optional | `col == value` |
| `between` | [min, max] | required | — | — | optional | `col < min OR col > max` |
| `in` | list | required | — | — | optional | `col NOT IN (...)` |
| `not_in` | list | required | — | — | optional | `col IN (...)` |
| `not_null` | — | required | — | — | optional | `col IS NULL` |
| `is_null` | — | required | — | — | optional | `col IS NOT NULL` |
| `unique` | — | required | — | — | optional | duplicate values exist |
| `min_length` | int | required | — | — | optional | `LENGTH(col) < value` |
| `max_length` | int | required | — | — | optional | `LENGTH(col) > value` |
| `pattern` | regex str | required | — | — | optional | `col !~ value` |
| `is_type` | type name | required | — | — | optional | type check fails |
| `column_lt` | — | required | — | required | optional | `col >= other_column` |
| `column_lte` | — | required | — | required | optional | `col > other_column` |
| `column_eq` | — | required | — | required | optional | `col != other_column` |
| `geometry_type` | list of types | required | — | — | optional | geom type not in list |
| `exactly_one_of` | — | — | required | — | **no** | 0 or 2+ non-null |
| `any_of` | — | — | required | — | **no** | all null |

**22 check types total.**
