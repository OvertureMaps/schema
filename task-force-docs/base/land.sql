SELECT
    -- Needed to compute ID and satisfy Overture requirements:
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,
    TO_ISO8601(created_at AT TIME ZONE 'UTC') AS update_time,

    -- Determine subtype from class:
    CASE
        -- Forest
        WHEN class IN ('forest', 'wood') THEN 'forest'

        -- Glacier
        WHEN class IN ('glacier') THEN 'glacier'

        -- Grass
        WHEN class IN ('fell','grass', 'grassland','meadow','tundra') THEN 'grass'

        -- Physical
        WHEN class IN (
            'hill',
            'peak',
            'plateau',
            'saddle',
            'valley',
            'volcano'
        ) THEN 'physical'

        -- Reef
        WHEN class IN ('reef') THEN 'reef'

        -- Rock
        WHEN class IN (
            'bare_rock',
            'rock',
            'scree',
            'shingle'
        ) THEN 'rock'

        --Sand
        WHEN class IN (
            'sand',
            'beach',
            'dune'
        ) THEN 'sand'

        --Shrub
        WHEN class IN (
            'heath',
            'scrub',
            'shrub',
            'shrubbery'
        ) THEN 'shrub'

        -- Tree
        WHEN class IN ('tree', 'tree_row') THEN 'tree'

        -- Wetland
        WHEN tags [ 'natural' ] IN ('wetland') THEN 'wetland'
    END AS subtype,
    class,

    -- Complex name logic gets injected here
    '__OVERTURE_NAMES_QUERY' AS names,

    -- Relevant OSM tags for land type
    MAP_FILTER(tags, (k,v) -> k IN (
            'landcover',
            'landuse',
            'natural',
            'surface'
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
            NULL
        )
        AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double
        )
    ) ] AS sources,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Elevation as integer (meters above sea level)
    TRY_CAST(tags['ele'] AS integer) AS elevation,

    wkt_geometry

FROM (
    SELECT
        *,
        -- Determine classes from OSM tags
        CASE
            -- Natural tags that map to specific classes:
            WHEN tags [ 'natural' ] IN (
                'bare_rock',
                'beach',
                'dune',
                'fell',
                'forest',
                'glacier',
                'grassland',
                'heath',
                'hill',
                'peak',
                'plateau',
                'reef',
                'rock',
                'sand',
                'saddle',
                'scree',
                'scrub',
                'shingle',
                'shrub',
                'shrubbery',
                'tree_row',
                'tree',
                'tundra',
                'valley',
                'volcano',
                'wetland',
                'wood'
            ) THEN tags [ 'natural' ]

            -- Surface tags that become classes
            WHEN tags [ 'surface' ] IN ('grass') THEN tags [ 'surface' ]
            WHEN tags [ 'landcover' ] = 'trees' THEN 'forest'
            WHEN tags [ 'landcover' ] IN ('grass', 'scrub', 'tree') THEN tags [ 'landcover' ]

            WHEN tags['name'] IS NULL AND tags [ 'meadow' ] IS NULL
                AND tags [ 'landuse' ] IN ('forest', 'meadow', 'grass') THEN tags [ 'landuse' ]
            ELSE NULL
        END AS class
    FROM (
        SELECT
            id,
            type,
            version,
            tags,
            created_at,
            -- ST_GeometryFromText(wkt) AS geom,
            wkt AS wkt_geometry,
            min_lon,
            max_lon,
            min_lat,
            max_lat
            -- These two lines get injected.
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
                OR tags [ 'landuse' ] IN ('forest', 'meadow', 'grass')
            )
            -- None of the below tags can be present; they go in other theme/types
            AND tags [ 'highway' ] IS NULL
            AND tags [ 'building' ] IS NULL
            AND tags [ 'golf' ] IS NULL
            AND tags [ 'sport' ] IS NULL
            AND tags [ 'leisure' ] IS NULL
    )
)
WHERE
    class IS NOT NULL -- Ignore anything that didn't get assigned a class
    AND (
        -- Polygons are always allowed
        wkt_geometry LIKE '%POLYGON%'

        -- Valid Point classes:
        OR (
            wkt_geometry LIKE '%POINT%'
            AND class IN ('hill', 'plateau', 'peak', 'tree', 'shrub', 'valley', 'volcano', 'saddle')
        )
        -- Valid LineStrings
        OR (
            wkt_geometry LIKE '%LINESTRING%'
            AND class = 'tree_row'
        )
    )

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
    -- Stub with today's date for now
    TO_ISO8601(cast(now() as timestamp) AT TIME ZONE 'UTC') AS update_time,
    class as subType,
    subclass as class,
    NULL AS names,
    MAP() AS source_tags,
    MAP() AS osm_tags,
    -- Source is OSM
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            NULL,
            NULL
        ) AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double
        )
    ) ] as sources,
    NULL AS wikidata,
    NULL AS elevation,
    wkt AS wkt_geometry
FROM {daylight_earth_table}
WHERE release = '{daylight_version}'
    AND theme = 'land'
    AND class = 'land'
    AND subclass = 'land'
