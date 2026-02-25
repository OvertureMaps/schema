# Venue

A concert venue.

A location where musical performances take place.

## Fields

| Name | Type | Description |
| -----: | :----: | ------------- |
| `id` | `Id` | Unique identifier |
| `category` | `"music"` | |
| `kind` | `"venue"` | |
| `name` | `string` (optional) | Venue name<br/>*At least one of `name`, `description` must be set* |
| `description` | `string` (optional) | *At least one of `name`, `description` must be set* |
| `geometry` | `geometry` | *Allowed geometry types: Point, Polygon* |
| `capacity` | `int64` (optional) | *`≥ 1`* |
| `resident_ensemble` | `Id` (optional) | A unique identifier<br/>*References `Instrument` (belongs to)* |

## Constraints

- At least one of `name`, `description` must be set
