Overture `base`` theme SQL files
===

Within the Overture `base` theme, there are 4 types that are derived exclusively from OpenStreetMap data:

 1. `infrastructure`
 1. `land`
 1. `land_use`
 1. `water`

The *tags* present on these features in OSM determine the `type`, `subtype`, and `class` for the feature in Overture. These SQL files contain the logic for all of these conversions.

Since features in OSM may have any number of tags, the order of the statements in these SQL files is important — i.e., the first `WHEN` statement that a feature matches will determine the `subtype` and `class`.

Each `WHEN` statement yields the following: `ROW(subtype, class)`

For example, the `rock` subtype in the `land` type is determined by the presence of the following _values_ of the `natural` tag in OSM:

```sql
 WHEN tags['natural'] IN (
       'bare_rock',
       'rock',
       'scree',
       'shingle',
       'stone'
   ) THEN ROW('rock', tags['natural'])
```

This results in the following classification:

| OSM Tag | Overture Subtype |Overture Class |
|----------|--------|-----|
|natural=bare_rock| rock | bare_rock|
|natural=rock| rock | rock |
|natural=scree| rock | scree|
|natural=shingle| rock | shingle|
|natural=stone| rock | stone|
