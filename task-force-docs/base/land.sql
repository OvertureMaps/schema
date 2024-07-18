-- This file contains the logic for transforming OpenStreetMap features into Overture features
-- for the `land` type within the `base` theme.

-- The order of the WHEN clauses in the following CASE statement is very specific. It is the same
-- as saying "WHEN this tag is present AND ignore any of the other tags below this line"
WITH classified_osm AS (
    SELECT CAST(
        CASE
            -- Desert
            WHEN tags['natural'] IN ('desert') THEN ROW('desert', tags['natural'])

            -- Wetland
            WHEN tags['natural'] IN ('wetland') THEN ROW('wetland', 'wetland')

            -- Glacier
            WHEN tags['natural'] IN ('glacier') THEN ROW('glacier', tags['natural'])

            -- Rock
            WHEN tags['natural'] IN (
                'bare_rock',
                'rock',
                'scree',
                'shingle',
                'stone'
            ) THEN ROW('rock', tags['natural'])

            -- Sand
            WHEN tags['natural'] IN ('beach', 'dune', 'sand') THEN ROW('sand', tags['natural'])

            -- Grass
            WHEN tags['natural'] IN (
                'fell',
                'grass',
                'grassland',
                'meadow',
                'tundra'
            ) THEN ROW('grass', tags['natural'])
            WHEN tags['landcover'] IN ('grass') THEN ROW ('grass', tags['landcover'])

            -- Shrub / Scrub
            WHEN tags['natural'] IN (
                'heath',
                'shrub',
                'shrubbery',
                'scrub'
            ) THEN ROW('shrub',tags['natural'])
            WHEN tags['landcover'] IN ('scrub') THEN ROW('shrub', tags['landcover'])

            -- Reefs
            WHEN tags['natural'] IN ('reef') THEN ROW('reef', tags['natural'])

            -- Forest
            WHEN tags['natural'] IN ('forest', 'wood') THEN ROW('forest', tags['natural'])
            WHEN tags['landcover'] IN ('trees') THEN ROW('forest', 'forest')
            WHEN tags['landuse'] IN ('forest') THEN ROW('forest','forest')

            -- Single trees tree rows
            WHEN tags['natural'] IN ('tree') THEN ROW('tree','tree')
            WHEN tags['natural'] IN ('tree_row') THEN ROW('tree','tree_row')

            -- Physical Subtype
            WHEN tags['natural'] IN(
                'cave_entrance',
                'cliff',
                'hill',
                'mountain_range',
                'peak',
                'peninsula',
                'ridge',
                'saddle',
                'valley'
            ) THEN ROW('physical', tags['natural'])

            -- Volcanoes
            WHEN tags['natural'] = 'volcano' THEN IF(
                tags['type'] = 'extinct' OR tags['volcano:status'] = 'extinct',
                ROW ('physical','peak'),
                ROW('physical','volcano')
            )

            -- Archipelagos, Islands & Islets
            WHEN tags['place'] IN (
                'archipelago',
                'island',
                'islet'
            ) THEN ROW('land',tags['place'])

            -- Look at surface tag now
            WHEN tags['surface'] IN ('grass') THEN ROW('grass','grass')

            ELSE ROW(NULL, NULL)
        END AS ROW(subtype varchar, class varchar)
        ) AS overture,

        -- Allowed surface tags
        CASE
            WHEN tags['surface'] IN (
                'asphalt',
                'cobblestone',
                'compacted',
                'concrete',
                'dirt',
                'earth',
                'fine_gravel',
                'grass',
                'gravel',
                'ground',
                'paved',
                'paving_stones',
                'pebblestone',
                'recreation_grass',
                'recreation_paved',
                'recreation_sand',
                'rubber',
                'sand',
                'sett',
                'tartan',
                'unpaved',
                'wood',
                'woodchips'
            )   THEN tags['surface']
            WHEN tags['surface'] = 'concrete:plates'
                THEN 'concrete_plates'
            ELSE NULL
        END AS surface,
        TRY_CAST(tags['ele'] AS integer) AS elevation,
        *
    FROM
        {daylight_table}
    WHERE
        release = '{daylight_version}'
        -- These tags are considered for the land type:
        AND
        (
            tags [ 'natural' ] IS NOT NULL
            OR tags [ 'surface' ] IS NOT NULL
            OR tags [ 'landcover' ] IS NOT NULL
            OR tags [ 'landuse' ] IN ('forest', 'meadow')
            OR tags [ 'place' ] IN ('archipelago','island','islet')
        )
        -- None of the below tags can be present; they go in other theme/types
        AND tags [ 'highway' ] IS NULL
        AND tags [ 'building' ] IS NULL
        AND tags [ 'golf' ] IS NULL
        AND tags [ 'leisure' ] IS NULL
)
SELECT
    -- Needed to compute ID and satisfy Overture requirements:
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,

    -- Complex name logic gets injected here
    '__OVERTURE_NAMES_QUERY' AS names,

    overture.subtype AS subtype,
    overture.class AS class,

    -- Relevant OSM tags for land type
    MAP_FILTER(tags, (k,v) -> k IN (
            'building',
            'denotation',
            'diameter_crown',
            'est_height',
            'genus',
            'golf',
            'height',
            'highway',
            'landcover',
            'landuse',
            'leaf_cycle',
            'leaf_type',
            'leisure',
            'meadow',
            'min_height',
            'natural',
            'place',
            'reef',
            'species',
            'sport',
            'surface',
            'taxon:cultivar',
            'taxon:species',
            'taxon',
            'type',
            'volcano:status',
            'volcano:type'
        )
    ) AS source_tags,

    -- Add all OSM Tags for debugging
    tags AS osm_tags,

    -- Sources are an array of structs.
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            SUBSTR(type, 1, 1) || CAST(id AS varchar) || '@' || CAST(version AS varchar),
            TO_ISO8601(created_at AT TIME ZONE 'UTC'),
            NULL
        )
        AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            update_time varchar,
            confidence double
        )
    ) ] AS sources,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Overture's concept of `layer` is called level
    TRY_CAST(tags['layer'] AS int) AS level,

    -- Elevation as meters above sea level
    IF(elevation < 9000, elevation, NULL) as elevation,

    -- Surface
    surface,

    wkt AS wkt_geometry

FROM
    classified_osm
WHERE
    overture.subtype IS NOT NULL

UNION ALL
-- Land derived from the OSM Coastline tool
SELECT
    -- Needed to compute ID and satisfy Overture requirements.
    'area' AS type,
    NULL AS id,
    0 version,
    ST_XMIN(ST_GeometryFromText(wkt)) as min_lon,
    ST_XMAX(ST_GeometryFromText(wkt)) as max_lon,
    ST_YMIN(ST_GeometryFromText(wkt)) AS min_lat,
    ST_YMAX(ST_GeometryFromText(wkt)) AS max_lat,
    NULL AS names,
    class as subtype,
    subclass as class,
    MAP() AS source_tags,
    MAP() AS osm_tags,
    -- Source is OSM
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            NULL,
            NULL,
            NULL
        ) AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            update_time varchar,
            confidence double
        )
    ) ] as sources,
    NULL AS wikidata,
    NULL AS level,
    NULL AS elevation,
    NULL AS surface,
    wkt AS wkt_geometry
FROM {daylight_earth_table}
WHERE release = '{daylight_version}'
    AND theme = 'land'
    AND class = 'land'
    AND subclass = 'land'
