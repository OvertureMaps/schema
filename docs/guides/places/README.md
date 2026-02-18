# Taxonomy Browser

An interactive tool for exploring and comparing Overture Maps Places taxonomy releases.

## Adding a New Release

To add a new release, only edit `taxonomy-browser.mdx` — no component code changes are needed.

### 1. Add CSV files

Place two CSV files in the `csv/` directory:

- **Data CSV**: Contains the taxonomy hierarchy and category mappings.
- **Counts CSV**: Contains place counts per category. Expected columns: `count`, `primary_category`, and optionally `basic_category`.

### 2. Add imports

At the top of `taxonomy-browser.mdx`, add raw-loader imports for your new files:

```js
import newDataCsv from '!!raw-loader!./csv/YYYY-MM-DD-New-Release.csv';
import newCountsCsv from '!!raw-loader!./csv/YYYY-MM-DD-counts.csv';
```

### 3. Add a release entry

Add an object to the `releases` array in `taxonomy-browser.mdx`:

```jsx
{
  id: 'uniqueId',
  label: 'Month (Short Description)',
  releaseUrl: 'https://docs.overturemaps.org/blog/...',
  note: 'Optional note displayed in the detail panel.',
  tags: [
    { label: 'DD Month YYYY', title: 'Date' },
    { label: 'YYYY-MM-DD.0', title: 'Data version' },
    { label: 'vX.Y.Z', title: 'Schema version' },
  ],
  dataCsv: newDataCsv,
  countsCsv: newCountsCsv,
  // Field mappings (see below)
  codeField: 'column_name',
  fieldNames: ['col1', 'col2', ...],
  basicCategoryField: 'basic_col_name' // or null
  // Plus one of the two hierarchy modes
}
```

### Hierarchy modes

Choose one depending on the structure of the data CSV:

**Multi-field** — The hierarchy is constructed by joining multiple columns. Use when the CSV has separate columns like `theme`, `category`, `sub_category`, etc.

```js
hierarchyFields: ['theme', 'category', 'sub_category', 'speciality'],
```

**Single-field** — The CSV already contains a `" > "`-delimited hierarchy string in one column.

```js
hierarchyField: 'hierarchy_column_name',
```

### Field reference

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique identifier for this release |
| `label` | Yes | Display label shown in the dropdown and section headers |
| `releaseUrl` | No | Link for the release date tag |
| `note` | No | Note shown in the collapsible detail section |
| `tags` | Yes | Array of `{ label, title }` for the info row |
| `dataCsv` | Yes | Raw-loader import of the data CSV |
| `countsCsv` | No | Raw-loader import of the counts CSV, or `null` |
| `fieldNames` | Yes | Column names in order, mapping CSV columns to object keys |
| `codeField` | Yes | Which field in `fieldNames` is the category code |
| `hierarchyFields` | * | Array of fields to join into a hierarchy path |
| `hierarchyField` | * | Single field containing a pre-built `" > "` hierarchy |
| `basicCategoryField` | No | Field holding the basic-level category label, or `null` |
| `enabled` | No | Set to `false` to hide this release from the built site. Defaults to `true` |
| `displayFields` | No | Array of `{ field, label }` for extra key/value rows in the detail panel |
| `matchColumn` | No | Column containing a code from another release for cross-tab matching |
| `matchType` | No | Which release's codes `matchColumn` maps to: `'original'` or `'new'` |

\* Exactly one of `hierarchyFields` or `hierarchyField` is required.

### Cross-tab matching

When category codes change between releases, set `matchColumn` and `matchType` so the detail panel can find the corresponding entry across tabs.

- `matchColumn` — a column in the data CSV that holds a code from a different release (e.g. `old_primary_category`)
- `matchType`:
  - `'original'` — the `matchColumn` values correspond to the first release's category codes. Use this when the column maps back to the original taxonomy.
  - `'new'` — the `matchColumn` values correspond to the immediately previous release's category codes. Use this when releases change incrementally.

This does two things:
1. **Cross-tab lookup**: entries are also indexed by the `matchColumn` value, so selecting a category on one tab finds the matching data in releases that renamed it.
2. **Change indicators**: `prevCount` is resolved using the `matchColumn` value against the appropriate prior release's counts.

If `matchColumn` is not set, cross-tab matching uses the `codeField` value directly (works when codes are the same across releases).

### Release ordering

Releases are compared in array order. The first release has no previous-release comparison. Each subsequent release computes change indicators against the one before it. Place new releases at the end of the array.

### Visibility and missing data

Set `enabled: false` on a release entry in `taxonomy-browser.mdx` to exclude it from the built site:

```jsx
{
  id: 'february',
  enabled: false,   // hidden from the site until ready
  label: 'February (Bug Fixes, Simplified Basic)',
  // ...
}
```

The release stays in the config for future use — just flip it to `true` (or remove the property) when ready. Only enabled releases appear in the dropdown, tree, and detail panel.

If `countsCsv` is `null`, the stats row shows "No Data" instead of counts, and the tree nodes won't display count badges.

### Display fields

Use `displayFields` to show extra key/value rows from the CSV data in the detail panel. Each entry maps a CSV column (`field`) to a label. Fields with empty values are automatically skipped.

```jsx
displayFields: [
  { field: 'match_type', label: 'Match Type' },
  { field: 'modified', label: 'Modified' },
],
```

These appear after the hierarchy levels and basic category, but before counts and percentile tags. Current releases use:

| Release | Display fields |
|---|---|
| April | `category_key` |
| October | `match_type`, `modified`, `remove_from_v1` |
| December | `old_primary_category`, `old_primary_hierarchy` |
| February | `new_display_name`, `is_basic`, `added`, `renamed`, `removed`, `redirect_to` |
